from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Employee ---
class EmployeeOut(BaseModel):
    id: int
    bitrix_id: int
    name: str
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool = True
    total_calls: int = 0
    avg_score: Optional[float] = None

    model_config = {"from_attributes": True}


class EmployeeScores(BaseModel):
    week: str
    greeting: Optional[float] = None
    needs_discovery: Optional[float] = None
    presentation: Optional[float] = None
    objection_handling: Optional[float] = None
    closing: Optional[float] = None
    initiative: Optional[float] = None
    overall: Optional[float] = None


class EmployeeProfile(EmployeeOut):
    score_trends: list[EmployeeScores] = []
    top_strengths: list[str] = []
    top_weaknesses: list[str] = []
    development_plan: list[str] = []
    priority_training: Optional[str] = None


# --- Transcript ---
class SegmentOut(BaseModel):
    start: float
    end: float
    text: str
    confidence: Optional[float] = None


class TranscriptOut(BaseModel):
    id: int
    text: str
    language: str = "ru"
    model_used: str = "small"
    confidence: Optional[float] = None
    segments: Optional[list[SegmentOut]] = None

    model_config = {"from_attributes": True}


# --- Analysis ---
class AnalysisOut(BaseModel):
    id: int
    call_id: int
    script_id: Optional[int] = None
    greeting_score: Optional[int] = None
    needs_discovery: Optional[int] = None
    presentation_score: Optional[int] = None
    objection_handling: Optional[int] = None
    closing_score: Optional[int] = None
    initiative_score: Optional[int] = None
    overall_score: Optional[int] = None
    summary: Optional[str] = None
    strengths: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None
    recommendations: Optional[list[str]] = None
    missed_script_steps: Optional[list[str]] = None
    who_leads: Optional[str] = None
    next_step_agreed: Optional[bool] = None
    crm_note_suggestion: Optional[str] = None
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Call ---
class CallOut(BaseModel):
    id: int
    bitrix_call_id: str
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    direction: str
    phone_number: Optional[str] = None
    duration_sec: int
    call_date: datetime
    deal_id: Optional[int] = None
    deal_name: Optional[str] = None
    deal_stage: Optional[str] = None
    deal_amount: Optional[float] = None
    status: str = "new"
    overall_score: Optional[int] = None
    who_leads: Optional[str] = None
    next_step_agreed: Optional[bool] = None

    model_config = {"from_attributes": True}


class CallDetail(CallOut):
    transcript: Optional[TranscriptOut] = None
    analysis: Optional[AnalysisOut] = None
    audio_url: Optional[str] = None


class CallListResponse(BaseModel):
    items: list[CallOut]
    total: int
    page: int
    page_size: int


# --- Export Job ---
class ExportJobCreate(BaseModel):
    period: str  # "1d", "7d", "14d", "30d", "quarter", "year"
    department_id: Optional[int] = None
    whisper_provider: str = "openai"  # "openai" or "local"


class ExportJobOut(BaseModel):
    id: int
    period: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    department_id: Optional[int] = None
    whisper_provider: str = "openai"
    status: str = "pending"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_calls: int = 0
    processed: int = 0
    transcribed: int = 0
    analyzed: int = 0
    error_msg: Optional[str] = None
    report_path: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Sales Script ---
class SalesScriptOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    content: str
    original_file: Optional[str] = None
    file_type: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SalesScriptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    content: str


class SalesScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


# --- Dashboard ---
class DashboardSummary(BaseModel):
    total_calls: int = 0
    total_employees: int = 0
    total_deals: int = 0
    avg_score: Optional[float] = None
    avg_duration: Optional[float] = None
    calls_with_next_step: int = 0
    calls_without_next_step: int = 0
    top_problems: list[str] = []
    top_recommendations: list[str] = []


class EmployeeRanking(BaseModel):
    employee_id: int
    name: str
    total_calls: int
    avg_greeting: Optional[float] = None
    avg_needs_discovery: Optional[float] = None
    avg_presentation: Optional[float] = None
    avg_objection_handling: Optional[float] = None
    avg_closing: Optional[float] = None
    avg_initiative: Optional[float] = None
    avg_overall: Optional[float] = None
    priority_training: Optional[str] = None


class TrendPoint(BaseModel):
    week: str
    avg_score: Optional[float] = None
    total_calls: int = 0


class ReanalyzeRequest(BaseModel):
    script_id: Optional[int] = None
