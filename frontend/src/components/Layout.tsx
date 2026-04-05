import { NavLink } from 'react-router-dom'
import { BarChart3, Phone, Users, FileText, Download } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Дашборд', icon: BarChart3 },
  { to: '/calls', label: 'Звонки', icon: Phone },
  { to: '/employees', label: 'Сотрудники', icon: Users },
  { to: '/scripts', label: 'Скрипты', icon: FileText },
  { to: '/exports', label: 'Выгрузки', icon: Download },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-lg font-bold text-gray-900">Call Analytics</h1>
          <p className="text-xs text-gray-500 mt-1">Анализ звонков отдела продаж</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
