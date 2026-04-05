import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Copy, Check } from 'lucide-react'
import AudioPlayer from '../components/AudioPlayer'
import ScoreBar from '../components/ScoreBar'
import { fetchCall, type CallDetail as CallDetailType } from '../api/client'
import { formatDateTime, formatDuration, directionLabel } from '../lib/utils'

export default function CallDetail() {
  const { id } = useParams<{ id: string }>()
  const [call, setCall] = useState<CallDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchCall(Number(id)).then(setCall).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-gray-500">Загрузка...</div>
  if (!call) return <div className="text-red-500">Звонок не найден</div>

  const analysis = call.analysis

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/calls" className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Звонок #{call.id}</h1>
          <p className="text-sm text-gray-500">
            {formatDateTime(call.call_date)} | {call.employee_name} | {directionLabel(call.direction)} | {formatDuration(call.duration_sec)}
          </p>
        </div>
      </div>

      {/* Call info */}
      <div className="grid grid-cols-4 gap-4">
        <InfoCard label="Менеджер" value={call.employee_name || '-'} />
        <InfoCard label="Клиент" value={call.phone_number || '-'} />
        <InfoCard label="Сделка" value={call.deal_name || '-'} />
        <InfoCard label="Стадия" value={call.deal_stage || '-'} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: Audio + Transcript */}
        <div className="space-y-4">
          {call.audio_url && (
            <div className="bg-white rounded-xl border p-6">
              <h2 className="text-lg font-semibold mb-4">Аудиозапись и транскрипт</h2>
              <AudioPlayer
                audioUrl={call.audio_url}
                segments={call.transcript?.segments}
              />
            </div>
          )}

          {!call.audio_url && call.transcript && (
            <div className="bg-white rounded-xl border p-6">
              <h2 className="text-lg font-semibold mb-4">Транскрипт</h2>
              <div className="max-h-96 overflow-y-auto">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{call.transcript.text}</p>
              </div>
              {call.transcript.confidence != null && (
                <p className="mt-2 text-xs text-gray-400">
                  Уверенность: {(call.transcript.confidence * 100).toFixed(1)}%
                </p>
              )}
            </div>
          )}
        </div>

        {/* Right: Analysis */}
        <div className="space-y-4">
          {analysis && (
            <>
              {/* Scores */}
              <div className="bg-white rounded-xl border p-6 space-y-3">
                <h2 className="text-lg font-semibold mb-2">Оценки</h2>
                <ScoreBar label="Приветствие" score={analysis.greeting_score} />
                <ScoreBar label="Выявление потребностей" score={analysis.needs_discovery} />
                <ScoreBar label="Презентация" score={analysis.presentation_score} />
                <ScoreBar label="Работа с возражениями" score={analysis.objection_handling} />
                <ScoreBar label="Закрытие" score={analysis.closing_score} />
                <ScoreBar label="Инициатива" score={analysis.initiative_score} />
                <div className="pt-2 border-t">
                  <ScoreBar label="Общая оценка" score={analysis.overall_score} />
                </div>
              </div>

              {/* Summary */}
              {analysis.summary && (
                <div className="bg-white rounded-xl border p-6">
                  <h3 className="font-semibold mb-2">Резюме</h3>
                  <p className="text-sm text-gray-700">{analysis.summary}</p>
                  <div className="mt-3 flex gap-4 text-sm">
                    <span>Кто ведёт: <strong>{analysis.who_leads || '-'}</strong></span>
                    <span>
                      Следующий шаг:{' '}
                      <strong className={analysis.next_step_agreed ? 'text-green-600' : 'text-red-500'}>
                        {analysis.next_step_agreed ? 'Да' : 'Нет'}
                      </strong>
                    </span>
                  </div>
                </div>
              )}

              {/* Strengths & Weaknesses */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-50 rounded-xl border border-green-200 p-4">
                  <h3 className="font-semibold text-green-800 mb-2">Сильные стороны</h3>
                  <ul className="space-y-1">
                    {(analysis.strengths || []).map((s, i) => (
                      <li key={i} className="text-sm text-green-700">+ {s}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-red-50 rounded-xl border border-red-200 p-4">
                  <h3 className="font-semibold text-red-800 mb-2">Слабые стороны</h3>
                  <ul className="space-y-1">
                    {(analysis.weaknesses || []).map((w, i) => (
                      <li key={i} className="text-sm text-red-700">- {w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Recommendations */}
              {analysis.recommendations && analysis.recommendations.length > 0 && (
                <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
                  <h3 className="font-semibold text-blue-800 mb-2">Рекомендации</h3>
                  <ul className="space-y-1">
                    {analysis.recommendations.map((r, i) => (
                      <li key={i} className="text-sm text-blue-700">{i + 1}. {r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Missed script steps */}
              {analysis.missed_script_steps && analysis.missed_script_steps.length > 0 && (
                <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-4">
                  <h3 className="font-semibold text-yellow-800 mb-2">Пропущенные шаги скрипта</h3>
                  <ul className="space-y-1">
                    {analysis.missed_script_steps.map((s, i) => (
                      <li key={i} className="text-sm text-yellow-700">{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* CRM note */}
              {analysis.crm_note_suggestion && (
                <div className="bg-white rounded-xl border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">Заметка для CRM</h3>
                    <button
                      onClick={() => copyToClipboard(analysis.crm_note_suggestion!)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-gray-100 rounded-lg hover:bg-gray-200"
                    >
                      {copied ? <Check size={14} /> : <Copy size={14} />}
                      {copied ? 'Скопировано' : 'Скопировать'}
                    </button>
                  </div>
                  <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                    {analysis.crm_note_suggestion}
                  </p>
                </div>
              )}
            </>
          )}

          {!analysis && (
            <div className="bg-white rounded-xl border p-6 text-center text-gray-400">
              Анализ ещё не проведён. Статус: {call.status}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-sm font-medium truncate">{value}</p>
    </div>
  )
}
