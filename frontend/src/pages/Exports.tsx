import { useEffect, useState, useCallback } from 'react'
import { Download, Play, RefreshCw, FileSpreadsheet } from 'lucide-react'
import { fetchExports, createExport, fetchExport, fetchExportReport, type ExportJob } from '../api/client'
import { formatDateTime, PERIODS } from '../lib/utils'

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидание',
  running: 'Выгрузка данных',
  transcribing: 'Транскрибация',
  analyzing: 'Анализ',
  generating_report: 'Генерация отчёта',
  completed: 'Завершено',
  failed: 'Ошибка',
  report_failed: 'Ошибка отчёта',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700',
  transcribing: 'bg-purple-100 text-purple-700',
  analyzing: 'bg-indigo-100 text-indigo-700',
  generating_report: 'bg-cyan-100 text-cyan-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  report_failed: 'bg-red-100 text-red-700',
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
      !['completed', 'failed', 'report_failed'].includes(e.status)
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

  const handleDownloadReport = async (jobId: number) => {
    try {
      const { url } = await fetchExportReport(jobId)
      window.open(url, '_blank')
    } catch {
      alert('Отчёт ещё не готов')
    }
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
      <div className="space-y-3">
        {loading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : exports.length === 0 ? (
          <p className="text-gray-400 text-center py-12">Нет выгрузок. Запустите первую!</p>
        ) : (
          exports.map(job => (
            <div key={job.id} className="bg-white rounded-xl border p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="font-medium">Выгрузка #{job.id}</h3>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[job.status] || 'bg-gray-100'}`}>
                    {STATUS_LABELS[job.status] || job.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {job.status === 'completed' && job.report_path && (
                    <button
                      onClick={() => handleDownloadReport(job.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-sm hover:bg-green-100"
                    >
                      <FileSpreadsheet size={14} />
                      Скачать отчёт
                    </button>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-6 text-sm text-gray-500">
                <span>Период: {PERIODS.find(p => p.value === job.period)?.label || job.period}</span>
                {job.date_from && <span>С: {formatDateTime(job.date_from)}</span>}
                {job.date_to && <span>По: {formatDateTime(job.date_to)}</span>}
                <span>Звонков: {job.total_calls}</span>
                {job.created_at && <span>Создано: {formatDateTime(job.created_at)}</span>}
              </div>

              {/* Progress bar */}
              {job.total_calls > 0 && !['completed', 'failed'].includes(job.status) && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>Обработано: {job.processed} / {job.total_calls}</span>
                    <span>{Math.round((job.processed / job.total_calls) * 100)}%</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${(job.processed / job.total_calls) * 100}%` }}
                    />
                  </div>
                </div>
              )}

              {job.error_msg && (
                <p className="mt-2 text-sm text-red-600 bg-red-50 rounded p-2">{job.error_msg}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
