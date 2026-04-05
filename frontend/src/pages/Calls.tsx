import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PeriodFilter from '../components/PeriodFilter'
import { fetchCalls, fetchEmployees, type Call, type Employee } from '../api/client'
import { formatDateTime, formatDuration, directionLabel, scoreColor, cn } from '../lib/utils'

export default function Calls() {
  const [period, setPeriod] = useState('30d')
  const [calls, setCalls] = useState<Call[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [employeeFilter, setEmployeeFilter] = useState('')
  const [directionFilter, setDirectionFilter] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEmployees().then(setEmployees)
  }, [])

  useEffect(() => {
    setLoading(true)
    const params: Record<string, string> = { period, page: String(page) }
    if (employeeFilter) params.employee_id = employeeFilter
    if (directionFilter) params.direction = directionFilter

    fetchCalls(params).then(data => {
      setCalls(data.items)
      setTotal(data.total)
    }).finally(() => setLoading(false))
  }, [period, page, employeeFilter, directionFilter])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Звонки</h1>
        <PeriodFilter value={period} onChange={v => { setPeriod(v); setPage(1) }} />
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={employeeFilter}
          onChange={e => { setEmployeeFilter(e.target.value); setPage(1) }}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Все сотрудники</option>
          {employees.map(e => (
            <option key={e.id} value={e.id}>{e.name}</option>
          ))}
        </select>
        <select
          value={directionFilter}
          onChange={e => { setDirectionFilter(e.target.value); setPage(1) }}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Все направления</option>
          <option value="incoming">Входящие</option>
          <option value="outgoing">Исходящие</option>
        </select>
        <span className="ml-auto text-sm text-gray-500 self-center">
          Всего: {total}
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Дата</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Менеджер</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Направление</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Клиент</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Длительность</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Сделка</th>
              <th className="px-4 py-3 text-center font-medium text-gray-500">Оценка</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Кто ведёт</th>
              <th className="px-4 py-3 text-center font-medium text-gray-500">Шаг</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-12 text-center text-gray-400">Загрузка...</td></tr>
            ) : calls.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-12 text-center text-gray-400">Нет звонков</td></tr>
            ) : (
              calls.map(call => (
                <tr key={call.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link to={`/calls/${call.id}`} className="text-blue-600 hover:underline">
                      {formatDateTime(call.call_date)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{call.employee_name || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      call.direction === 'incoming' ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'
                    }`}>
                      {directionLabel(call.direction)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{call.phone_number || '-'}</td>
                  <td className="px-4 py-3 tabular-nums">{formatDuration(call.duration_sec)}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{call.deal_name || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn('font-bold', scoreColor(call.overall_score))}>
                      {call.overall_score ?? '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{call.who_leads || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    {call.next_step_agreed != null && (
                      <span className={call.next_step_agreed ? 'text-green-600' : 'text-red-500'}>
                        {call.next_step_agreed ? 'Да' : 'Нет'}
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex justify-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50"
          >
            Назад
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-500">
            Страница {page} из {Math.ceil(total / 50)}
          </span>
          <button
            disabled={page >= Math.ceil(total / 50)}
            onClick={() => setPage(p => p + 1)}
            className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50"
          >
            Далее
          </button>
        </div>
      )}
    </div>
  )
}
