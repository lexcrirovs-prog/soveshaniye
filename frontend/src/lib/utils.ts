import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function scoreColor(score?: number): string {
  if (score == null) return 'text-gray-400'
  if (score <= 3) return 'text-red-600'
  if (score <= 6) return 'text-yellow-600'
  return 'text-green-600'
}

export function scoreBg(score?: number): string {
  if (score == null) return 'bg-gray-100'
  if (score <= 3) return 'bg-red-100'
  if (score <= 6) return 'bg-yellow-100'
  return 'bg-green-100'
}

export function directionLabel(dir: string): string {
  return dir === 'incoming' ? 'Входящий' : 'Исходящий'
}

export const PERIODS = [
  { value: '1d', label: 'Сегодня' },
  { value: '7d', label: '7 дней' },
  { value: '14d', label: '14 дней' },
  { value: '30d', label: '30 дней' },
  { value: 'quarter', label: 'Квартал' },
  { value: 'year', label: 'Год' },
] as const
