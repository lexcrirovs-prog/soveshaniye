import { cn, scoreBg, scoreColor } from '../lib/utils'

interface Props {
  label: string
  score?: number
  maxScore?: number
}

export default function ScoreBar({ label, score, maxScore = 10 }: Props) {
  const pct = score != null ? (score / maxScore) * 100 : 0

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className={cn('font-semibold', scoreColor(score))}>
          {score != null ? score : '-'}/{maxScore}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            score != null && score <= 3 && 'bg-red-500',
            score != null && score > 3 && score <= 6 && 'bg-yellow-500',
            score != null && score > 6 && 'bg-green-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
