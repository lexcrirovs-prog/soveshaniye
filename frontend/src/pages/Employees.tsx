import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchEmployees, type Employee } from '../api/client'
import { cn, scoreColor } from '../lib/utils'

export default function Employees() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEmployees().then(setEmployees).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500">Загрузка...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Сотрудники</h1>

      <div className="grid grid-cols-3 gap-4">
        {employees.map(emp => (
          <Link
            key={emp.id}
            to={`/employees/${emp.id}`}
            className="bg-white rounded-xl border p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">{emp.name}</h3>
              <span className={cn('text-2xl font-bold', scoreColor(emp.avg_score))}>
                {emp.avg_score != null ? emp.avg_score.toFixed(1) : '-'}
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-3">{emp.position || 'Менеджер'}</p>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Звонков: {emp.total_calls}</span>
              {emp.avg_score != null && (
                <div className="h-2 w-24 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full',
                      emp.avg_score <= 3 && 'bg-red-500',
                      emp.avg_score > 3 && emp.avg_score <= 6 && 'bg-yellow-500',
                      emp.avg_score > 6 && 'bg-green-500',
                    )}
                    style={{ width: `${(emp.avg_score / 10) * 100}%` }}
                  />
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>

      {employees.length === 0 && (
        <div className="text-center text-gray-400 py-12">
          Нет данных о сотрудниках. Запустите выгрузку из Битрикс24.
        </div>
      )}
    </div>
  )
}
