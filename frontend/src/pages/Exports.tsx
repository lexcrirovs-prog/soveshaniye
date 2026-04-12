import { useEffect, useState, useCallback } from 'react'
import { Play, RefreshCw, Download, CheckCircle2, Loader2, Clock, AlertCircle, StopCircle, XCircle } from 'lucide-react'
import { fetchExports, createExport, fetchExport, fetchExportReport, cancelExport, type ExportJob } from '../api/client'
import { formatDateTime, PERIODS } from '../lib/utils'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  pending:           { label: 'Ожидание',           color: 'bg-gray-100 text-gray-600',     icon: Clock },
  running:           { label: 'Загрузка данных',     color: 'bg-blue-100 text-blue-700',     icon: Loader2 },
  transcribing:      { label: 'Транскрибация',       color: 'bg-purple-100 text-purple-700', icon: Loader2 },
  analyzing:         { label: 'Анализ GPT-4o',       color: 'bg-indigo-100 text-indigo-700', icon: Loader2 },
  generating_report: { label: 'Генерация отчёта',    color: 'bg-cyan-100 text-cyan-700',     icon: Loader2 },
  completed:         { label: 'Завершено',           color: 'bg-green-100 text-green-700',   icon: CheckCircle2 },
  cancelled:         { label: 'Отменено',             color: 'bg-orange-100 text-orange-700', icon: XCircle },
  failed:            { label: 'Ошибка',              color: 'bg-red-100 text-red-700',       icon: AlertCircle },
  report_failed:     { label: 'Ошибка отчёта',       color: 'bg-red-100 text-red-700',       icon: AlertCircle },
}

const STAGES = [
  { key: 'download',   label: 'Загрузка',       field: 'processed'   as const, activeStatus: ['running'] },
  { key: 'transcribe', label: 'Транскрибация',  field: 'transcribed' as const, activeStatus: ['transcribing'] },
  { key: 'analyze',    label: 'Анализ',         field: 'analyzed'    as const, activeStatus: ['analyzing'] },
  { key: 'report',     label: 'Отчёт',          field: null,                   activeStatus: ['generating_report'] },
]

function pct(value: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(Math.round((value / total) * 100), 100)
}

function StageRow({ label, value, total, isActive, isDone }: {
  label: string; value: number; total: number; isActive: boolean; isDone: boolean
}) {
  const percent = pct(value, total)
  const barColor = isDone ? 'bg-green-500' : isActive ? 'bg-blue-500' : 'bg-gray-200'
  const textColor = isDone ? 'text-green-600' : isActive ? 'text-blue-600' : 'text-gray-400'

  return (
    <div className="flex items-center gap-3">
      <div className="w-28 text-xs font-medium text-gray-600 text-right shrink-0">{label}</div>
      <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${isDone ? 100 : percent}%` }}
        />
      </div>
      <div className={`w-20 text-xs font-semibold text-right shrink-0 ${textColor}`}>
        {isDone ? (
          <span className="flex items-center justify-end gap-1">
            <CheckCircle2 size={12} /> 100%
          </span>
        ) : isActive ? (
          <span className="flex items-center justify-end gap-1">
            <Loader2 size={12} className="animate-spin" /> {percent}%
          </span>
        ) : total > 0 ? (
          `${percent}%`
        ) : (
          '—'
        )}
      </div>
      <div className="w-24 text-xs text-gray-400 text-right shrink-0">
        {total > 0 ? `${value} / ${total}` : ''}
      </div>
    </div>
  )
}

function OverallProgress({ job }: { job: ExportJob }) {
  const total = job.total_calls
  if (total <= 0 && job.status === 'pending') return null

  const isFinished = ['completed', 'failed', 'report_failed', 'cancelled'].includes(job.status)

  // Calculate overall progress: 4 stages, each worth 25%
  let overall = 0
  if (total > 0) {
    overall += pct(job.processed, total) * 0.25
    overall += pct(job.transcribed, total) * 0.25
    overall += pct(job.analyzed, total) * 0.25
  }
  if (job.status === 'generating_report') overall += 12.5
  if (isFinished) overall = 100

  const stageOrder = ['pending', 'running', 'transcribing', 'analyzing', 'generating_report', 'completed']
  const currentIdx = stageOrder.indexOf(job.status)

  const isStageActive = (activeStatuses: string[]) => activeStatuses.includes(job.status)
  const isStageDone = (activeStatuses: string[]) => {
    const stageIdx = Math.max(...activeStatuses.map(s => stageOrder.indexOf(s)))
    return currentIdx > stageIdx || isFinished
  }

  return (
    <div className="mt-4 space-y-3">
      {/* Overall percentage */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">
          Общий прогресс
        </span>
        <span className="text-lg font-bold text-blue-600">
          {Math.round(overall)}%
        </span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${isFinished ? (job.status === 'completed' ? 'bg-green-500' : job.status === 'cancelled' ? 'bg-orange-400' : 'bg-red-500') : 'bg-blue-500'}`}
          style={{ width: `${overall}%` }}
        />
      </div>

      {/* Per-stage breakdown */}
      <div className="space-y-2 pt-1">
        {STAGES.map(stage => {
          const value = stage.field ? job[stage.field] : (job.status === 'completed' ? 1 : 0)
          const stageTotal = stage.field ? total : 1

          return (
            <StageRow
              key={stage.key}
              label={stage.label}
              value={value}
              total={stageTotal}
              isActive={isStageActive(stage.activeStatus)}
              isDone={isStageDone(stage.activeStatus)}
            />
          )
        })}
      </div>
    </div>
  )
}

export default function Exports() {
  const [exports, setExports] = useState<ExportJob[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState('7d')
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    fetchExports().then(setExports).finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  // Poll active jobs
  useEffect(() => {
    const activeJobs = exports.filter(e =>
      !['completed', 'failed', 'report_failed', 'cancelled'].includes(e.status)
    )
    if (activeJobs.length === 0) return

    const interval = setInterval(async () => {
      const updated = await Promise.all(
        activeJobs.map(j => fetchExport(j.id))
      )
      setExports(prev =>
        prev.map(e => {
          const u = updated.find(u => u.id === e.id)
          return u || e
        })
      )
    }, 3000)

    return () => clearInterval(interval)
  }, [exports])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const job = await createExport(selectedPeriod)
      setExports(prev => [job, ...prev])
    } finally {
      setCreating(false)
    }
  }

  const handleCancel = async (jobId: number) => {
    if (!confirm('Остановить выгрузку?')) return
    try {
      await cancelExport(jobId)
      setExports(prev =>
        prev.map(e => e.id === jobId ? { ...e, status: 'cancelled' } : e)
      )
    } catch {
      alert('Не удалось отменить')
    }
  }

  const handleDownloadReport = async (jobId: number) => {
    try {
      const { url } = await fetchExportReport(jobId)
      window.open(url, '_blank')
    } catch {
      alert('Отчёт ещё не готов')
    }
  }

  const elapsed = (job: ExportJob): string | null => {
    if (!job.started_at) return null
    const start = new Date(job.started_at).getTime()
    const end = job.finished_at ? new Date(job.finished_at).getTime() : Date.now()
    const sec = Math.floor((end - start) / 1000)
    const m = Math.floor(sec / 60)
    const s = sec % 60
    if (m > 0) return `${m} мин ${s} сек`
    return `${s} сек`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Выгрузки</h1>
        <button onClick={load} className="p-2 hover:bg-gray-100 rounded-lg" title="Обновить">
          <RefreshCw size={18} />
        </button>
      </div>

      {/* New export */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Новая выгрузка</h2>
        <div className="flex items-center gap-4">
          <select
            value={selectedPeriod}
            onChange={e => setSelectedPeriod(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            {PERIODS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
          >
            <Play size={16} />
            {creating ? 'Запуск...' : 'Запустить выгрузку'}
          </button>
        </div>
      </div>

      {/* Jobs list */}
      <div className="space-y-4">
        {loading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : exports.length === 0 ? (
          <p className="text-gray-400 text-center py-12">Нет выгрузок. Запустите первую!</p>
        ) : (
          exports.map(job => {
            const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending
            const StatusIcon = cfg.icon
            const time = elapsed(job)
            const isActive = !['completed', 'failed', 'report_failed', 'pending', 'cancelled'].includes(job.status)
            const canCancel = !['completed', 'failed', 'report_failed', 'cancelled'].includes(job.status)

            return (
              <div key={job.id} className="bg-white rounded-xl border p-5">
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-lg">Выгрузка #{job.id}</h3>
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${cfg.color}`}>
                      <StatusIcon size={12} className={isActive ? 'animate-spin' : ''} />
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {canCancel && (
                      <button
                        onClick={() => handleCancel(job.id)}
                        className="flex items-center gap-1.5 px-3 py-2 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100 transition-colors"
                      >
                        <StopCircle size={14} />
                        Остановить
                      </button>
                    )}
                    {job.status === 'completed' && job.report_path && (
                      <button
                        onClick={() => handleDownloadReport(job.id)}
                        className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
                      >
                        <Download size={14} />
                        Скачать отчёт
                      </button>
                    )}
                  </div>
                </div>

                {/* Meta info */}
                <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-gray-500">
                  <span>Период: {PERIODS.find(p => p.value === job.period)?.label || job.period}</span>
                  {job.date_from && <span>С: {formatDateTime(job.date_from)}</span>}
                  {job.date_to && <span>По: {formatDateTime(job.date_to)}</span>}
                  <span>Звонков: {job.total_calls}</span>
                  {time && <span>Время: {time}</span>}
                </div>

                {/* Progress visualization */}
                <OverallProgress job={job} />

                {/* Error */}
                {job.error_msg && (
                  <p className="mt-3 text-sm text-red-600 bg-red-50 rounded-lg p-3">{job.error_msg}</p>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
