import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import { Phone, Users, Target, TrendingUp } from 'lucide-react'
import PeriodFilter from '../components/PeriodFilter'
import {
  fetchDashboardSummary, fetchDashboardScores, fetchDashboardTrends,
  type DashboardSummary, type EmployeeRanking, type TrendPoint,
} from '../api/client'

export default function Dashboard() {
  const [period, setPeriod] = useState('30d')
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [scores, setScores] = useState<EmployeeRanking[]>([])
  const [trends, setTrends] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchDashboardSummary({ period }),
      fetchDashboardScores({ period }),
      fetchDashboardTrends({ period }),
    ]).then(([s, sc, t]) => {
      setSummary(s)
      setScores(sc)
      setTrends(t)
    }).finally(() => setLoading(false))
  }, [period])

  if (loading) return <div className="text-gray-500">Загрузка...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Дашборд</h1>
        <PeriodFilter value={period} onChange={setPeriod} />
      </div>

      {/* Stats cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard icon={Phone} label="Звонков" value={summary.total_calls} />
          <StatCard icon={Users} label="Сотрудников" value={summary.total_employees} />
          <StatCard icon={Target} label="Сделок" value={summary.total_deals} />
          <StatCard
            icon={TrendingUp}
            label="Средняя оценка"
            value={summary.avg_score != null ? summary.avg_score.toFixed(1) : '-'}
            color={
              summary.avg_score != null
                ? summary.avg_score > 6 ? 'text-green-600' : summary.avg_score > 3 ? 'text-yellow-600' : 'text-red-600'
                : ''
            }
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Employee ranking chart */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4">Рейтинг менеджеров</h2>
          {scores.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={scores} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 10]} />
                <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="avg_overall" fill="#3b82f6" name="Общая оценка" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-12">Нет данных</p>
          )}
        </div>

        {/* Trends chart */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-4">Тренд оценок</h2>
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 10]} />
                <Tooltip />
                <Line type="monotone" dataKey="avg_score" stroke="#3b82f6" strokeWidth={2} name="Средняя оценка" />
                <Line type="monotone" dataKey="total_calls" stroke="#9ca3af" strokeWidth={1} name="Звонков" yAxisId={0} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-12">Нет данных</p>
          )}
        </div>
      </div>

      {/* Top problems & recommendations */}
      {summary && (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border p-6">
            <h2 className="text-lg font-semibold mb-3">Топ проблемы</h2>
            {summary.top_problems.length > 0 ? (
              <ul className="space-y-2">
                {summary.top_problems.map((p, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="text-red-500 font-bold">{i + 1}.</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-400 text-sm">Нет данных</p>
            )}
          </div>
          <div className="bg-white rounded-xl border p-6">
            <h2 className="text-lg font-semibold mb-3">Рекомендации</h2>
            {summary.top_recommendations.length > 0 ? (
              <ul className="space-y-2">
                {summary.top_recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="text-blue-500 font-bold">{i + 1}.</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-400 text-sm">Нет данных</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ComponentType<{ size?: number }>
  label: string
  value: string | number
  color?: string
}) {
  return (
    <div className="bg-white rounded-xl border p-5">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-blue-50 rounded-lg">
          <Icon size={18} />
        </div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${color || 'text-gray-900'}`}>{value}</p>
    </div>
  )
}
