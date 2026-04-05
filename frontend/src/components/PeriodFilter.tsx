import { PERIODS } from '../lib/utils'

interface Props {
  value: string
  onChange: (value: string) => void
}

export default function PeriodFilter({ value, onChange }: Props) {
  return (
    <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
      {PERIODS.map(({ value: v, label }) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            value === v
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
