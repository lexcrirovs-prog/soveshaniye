import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import ScoreBar from '../components/ScoreBar'
import { fetchEmployee, fetchEmployeeCalls, fetchEmployeeScores, type EmployeeProfile, type Call, type ScoreTrend } from '../api/client'
import { formatDateTime, formatDuration, directionLabel, cn, scoreColor } from '../lib/utils'

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>()
  const [employee, setEmployee] = useState<EmployeeProfile | null>(null)
  const [calls, setCalls] = useState<Call[]>([])
  const [scores, setScores] = useState<ScoreTrend[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const eid = Number(id)
    setLoading(true)
    Promise.all([
      fetchEmployee(eid),
      fetchEmployeeCalls(eid),
      fetchEmployeeScores(eid),
    ]).then(([e, c, s]) => {
      setEmployee(e)
      setCalls(c)
      setScores(s)
    }).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-gray-500">Загрузка...</div>
  if (!employee) return <div className="text-red-500">Сотрудник не найден</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/employees" className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{employee.name}</h1>
          <p className="text-sm text-gray-500">{employee.position || 'Менеджер'} | Звонков: {employee.total_calls}</p>
        </div>
        <div className="ml-auto">
          <span className={cn('text-4xl font-bold', scoreColor(employee.avg_score))}>
            {employee.avg_score != null ? employee.avg_score.toFixed(1) : '-'}
          </span>
          <span className="text-sm text-gray-400 ml-1">/10</span>
        </div>
      </div>

      {/* Score trends chart */}
      {scores.length > 0 && (
        <div className="bg-white rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4">Динамика оценок</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={scores}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 10]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="overall" stroke="#3b82f6" strokeWidth={2} name="Общая" />
              <Line type="monotone" dataKey="greeting" stroke="#10b981" strokeWidth={1} name="Приветствие" />
              <Line type="monotone" dataKey="needs_discovery" stroke="#f59e0b" strokeWidth={1} name="Потребности" />
              <Line type="monotone" dataKey="presentation" stroke="#8b5cf6" strokeWidth={1} name="Презентация" />
              <Line type="monotone" dataKey="closing" stroke="#ef4444" strokeWidth={1} name="Закрытие" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Strengths & Weaknesses */}
        <div className="space-y-4">
          {employee.top_strengths.length > 0 && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-5">
              <h3 className="font-semibold text-green-800 mb-3">Сильные стороны</h3>
              <ul className="space-y-2">
                {employee.top_strengths.map((s, i) => (
                  <li key={i} className="text-sm text-green-700">+ {s}</li>
                ))}
              </ul>
            </div>
          )}
          {employee.top_weaknesses.length > 0 && (
            <div className="bg-red-50 rounded-xl border border-red-200 p-5">
              <h3 className="font-semibold text-red-800 mb-3">Зоны роста</h3>
              <ul className="space-y-2">
                {employee.top_weaknesses.map((w, i) => (
                  <li key={i} className="text-sm text-red-700">- {w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Development plan */}
        <div>
          {employee.development_plan.length > 0 && (
            <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
              <h3 className="font-semibold text-blue-800 mb-3">План развития</h3>
              <ul className="space-y-2">
                {employee.development_plan.map((d, i) => (
                  <li key={i} className="text-sm text-blue-700">{i + 1}. {d}</li>
                ))}
              </ul>
            </div>
          )}
          {employee.priority_training && (
            <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-5 mt-4">
              <h3 className="font-semibold text-yellow-800 mb-2">Приоритет обучения</h3>
              <p className="text-sm text-yellow-700">{employee.priority_training}</p>
            </div>
          )}
        </div>
      </div>

      {/* Calls table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Звонки</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Дата</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Направление</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Клиент</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Длительность</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Сделка</th>
              <th className="px-4 py-3 text-center font-medium text-gray-500">Оценка</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {calls.map(call => (
              <tr key={call.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link to={`/calls/${call.id}`} className="text-blue-600 hover:underline">
                    {formatDateTime(call.call_date)}
                  </Link>
                </td>
                <td className="px-4 py-3">{directionLabel(call.direction)}</td>
                <td className="px-4 py-3 text-gray-600">{call.phone_number || '-'}</td>
                <td className="px-4 py-3 tabular-nums">{formatDuration(call.duration_sec)}</td>
                <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{call.deal_name || '-'}</td>
                <td className="px-4 py-3 text-center">
                  <span className={cn('font-bold', scoreColor(call.overall_score))}>
                    {call.overall_score ?? '-'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
