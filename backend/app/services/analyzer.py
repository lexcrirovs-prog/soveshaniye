import json
import logging
import re
from typing import Any, Optional

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

CALL_ANALYSIS_SYSTEM_PROMPT = """Ты — старший аналитик отдела продаж B2B-компании, специализирующейся на промышленном оборудовании (котлы, теплообменники, автоматика). Проведи детальный анализ телефонного разговора менеджера с клиентом."""

CALL_ANALYSIS_USER_PROMPT = """КОНТЕКСТ:
- Менеджер: {employee_name}
- Направление звонка: {direction}
- Длительность: {duration} сек
- Связанная сделка: {deal_name} (стадия: {stage})

{script_section}

ТРАНСКРИПТ РАЗГОВОРА:
{transcript}

ПРОВЕДИ АНАЛИЗ ПО СЛЕДУЮЩИМ КРИТЕРИЯМ (оценка 1-10 для каждого):

1. ПРИВЕТСТВИЕ И УСТАНОВЛЕНИЕ КОНТАКТА
   - Представился ли менеджер (имя, компания)?
   - Уточнил ли имя клиента?
   - Обозначил ли цель звонка?

2. ВЫЯВЛЕНИЕ ПОТРЕБНОСТЕЙ
   - Задавал ли открытые вопросы?
   - Использовал ли технику SPIN (ситуация, проблема, извлечение, направление)?
   - Слушал ли клиента или перебивал?
   - Выяснил ли бюджет, сроки, ЛПР?

3. ПРЕЗЕНТАЦИЯ РЕШЕНИЯ
   - Привязал ли характеристики к потребностям клиента?
   - Использовал ли язык выгод (не характеристик)?
   - Привёл ли кейсы/примеры?

4. РАБОТА С ВОЗРАЖЕНИЯМИ
   - Как отреагировал на «дорого» / «подумаю» / «у конкурентов дешевле»?
   - Использовал ли алгоритм: выслушать → присоединиться → аргументировать → проверить?
   - Не сдался ли при первом отказе?

5. ЗАКРЫТИЕ И ФИКСАЦИЯ СЛЕДУЮЩЕГО ШАГА
   - Договорился ли о конкретном следующем действии?
   - Зафиксировал ли дату и время?
   - Кто взял инициативу — менеджер или клиент?

6. АКТИВНОСТЬ И ИНИЦИАТИВА
   - Кто ведёт разговор — менеджер или клиент?
   - Проявляет ли менеджер проактивность?
   - Создаёт ли срочность и ценность?

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "scores": {{
    "greeting": <1-10>,
    "needs_discovery": <1-10>,
    "presentation": <1-10>,
    "objection_handling": <1-10>,
    "closing": <1-10>,
    "initiative": <1-10>,
    "overall": <1-10>
  }},
  "summary": "<2-3 предложения: суть разговора>",
  "strengths": ["<сильная сторона 1 + цитата>", "..."],
  "weaknesses": ["<слабая сторона 1 + цитата>", "..."],
  "missed_script_steps": ["<пропущенный этап скрипта>", "..."],
  "recommendations": ["<конкретная рекомендация>", "..."],
  "who_leads": "менеджер" | "клиент" | "паритет",
  "next_step_agreed": true | false,
  "crm_note_suggestion": "<текст, который менеджер должен был занести в CRM>"
}}"""

EMPLOYEE_AGGREGATE_PROMPT = """На основе {count} проанализированных звонков менеджера {name} за период {date_from} — {date_to}, составь профиль:

ДАННЫЕ ЗВОНКОВ:
{analyses_json}

СФОРМИРУЙ (ответ строго в JSON):
{{
  "avg_scores": {{
    "greeting": <float>,
    "needs_discovery": <float>,
    "presentation": <float>,
    "objection_handling": <float>,
    "closing": <float>,
    "initiative": <float>,
    "overall": <float>
  }},
  "trend": "улучшается" | "ухудшается" | "стабильно",
  "top_problems": ["<системная проблема 1>", "<системная проблема 2>", "<системная проблема 3>"],
  "top_strengths": ["<сильная сторона 1>", "<сильная сторона 2>", "<сильная сторона 3>"],
  "development_plan": ["<действие 1 на следующую неделю>", "<действие 2>", "<действие 3>"],
  "priority_training": "<один навык, который даст максимальный рост конверсии>"
}}"""

DEPARTMENT_AGGREGATE_PROMPT = """На основе анализа всех менеджеров, сформируй отчёт для руководителя отдела продаж:

ДАННЫЕ ПО МЕНЕДЖЕРАМ:
{profiles_json}

СФОРМИРУЙ (ответ строго в JSON):
{{
  "ranking": [
    {{"name": "<ФИО>", "overall_score": <float>, "total_calls": <int>}}
  ],
  "systemic_problems": ["<проблема, встречающаяся у 2+ менеджеров>", "..."],
  "best_practices": ["<что делает лучший менеджер, чего не делают остальные>", "..."],
  "priority_actions": ["<действие для руководителя 1>", "...(всего 5)"],
  "training_recommendations": {{
    "group_trainings": ["<тема группового тренинга>", "..."],
    "individual_coaching": [{{"name": "<ФИО>", "topic": "<тема коучинга>"}}]
  }}
}}"""


def _parse_json_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error("Failed to parse JSON from response: %s", text[:500])
    return None


def analyze_call(
    transcript: str,
    employee_name: str,
    direction: str,
    duration: int,
    deal_name: str = "Не указана",
    stage: str = "Не указана",
    sales_script: Optional[str] = None,
) -> Optional[dict]:
    """Analyze a single call transcript using Claude API."""
    if not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None

    script_section = ""
    if sales_script:
        script_section = f"""СКРИПТ ПРОДАЖ, ПО КОТОРОМУ ДОЛЖЕН РАБОТАТЬ МЕНЕДЖЕР:
{sales_script}

Оцени соответствие разговора этому скрипту. Отметь пропущенные этапы и отклонения."""

    user_prompt = CALL_ANALYSIS_USER_PROMPT.format(
        employee_name=employee_name,
        direction="входящий" if direction == "incoming" else "исходящий",
        duration=duration,
        deal_name=deal_name,
        stage=stage,
        script_section=script_section,
        transcript=transcript,
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=CALL_ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        response_text = message.content[0].text
        result = _parse_json_response(response_text)
        if result:
            result["_raw_response"] = response_text
            result["_model_used"] = settings.anthropic_model
        return result
    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        return None


def aggregate_employee(
    analyses: list[dict[str, Any]],
    employee_name: str,
    date_from: str,
    date_to: str,
) -> Optional[dict]:
    """Generate aggregated employee profile from multiple call analyses."""
    if not settings.anthropic_api_key or not analyses:
        return None

    prompt = EMPLOYEE_AGGREGATE_PROMPT.format(
        count=len(analyses),
        name=employee_name,
        date_from=date_from,
        date_to=date_to,
        analyses_json=json.dumps(analyses, ensure_ascii=False, indent=2),
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json_response(message.content[0].text)
    except Exception as e:
        logger.error("Employee aggregation failed: %s", e)
        return None


def aggregate_department(profiles: list[dict[str, Any]]) -> Optional[dict]:
    """Generate department-level analysis from employee profiles."""
    if not settings.anthropic_api_key or not profiles:
        return None

    prompt = DEPARTMENT_AGGREGATE_PROMPT.format(
        profiles_json=json.dumps(profiles, ensure_ascii=False, indent=2),
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json_response(message.content[0].text)
    except Exception as e:
        logger.error("Department aggregation failed: %s", e)
        return None
