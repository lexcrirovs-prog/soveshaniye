import { useEffect, useRef, useState } from 'react'
import { Play, Pause, SkipBack, SkipForward } from 'lucide-react'
import type { Segment } from '../api/client'
import { formatDuration } from '../lib/utils'

interface Props {
  audioUrl: string
  segments?: Segment[]
  onTimeUpdate?: (time: number) => void
}

export default function AudioPlayer({ audioUrl, segments, onTimeUpdate }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [activeSegment, setActiveSegment] = useState<number>(-1)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime)
      onTimeUpdate?.(audio.currentTime)

      if (segments) {
        const idx = segments.findIndex(
          s => audio.currentTime >= s.start && audio.currentTime <= s.end
        )
        setActiveSegment(idx)
      }
    }

    const handleLoadedMetadata = () => setDuration(audio.duration)
    const handleEnded = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [segments, onTimeUpdate])

  const togglePlay = () => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.pause()
    } else {
      audio.play()
    }
    setIsPlaying(!isPlaying)
  }

  const seek = (time: number) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
  }

  const skipBack = () => seek(Math.max(0, currentTime - 10))
  const skipForward = () => seek(Math.min(duration, currentTime + 10))

  const seekToSegment = (idx: number) => {
    if (!segments || !segments[idx]) return
    seek(segments[idx].start)
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="space-y-4">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      {/* Controls */}
      <div className="flex items-center gap-4">
        <button onClick={skipBack} className="p-2 hover:bg-gray-100 rounded-lg">
          <SkipBack size={18} />
        </button>
        <button
          onClick={togglePlay}
          className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700"
        >
          {isPlaying ? <Pause size={20} /> : <Play size={20} />}
        </button>
        <button onClick={skipForward} className="p-2 hover:bg-gray-100 rounded-lg">
          <SkipForward size={18} />
        </button>

        <span className="text-sm text-gray-500 tabular-nums">
          {formatDuration(Math.floor(currentTime))} / {formatDuration(Math.floor(duration))}
        </span>
      </div>

      {/* Progress bar */}
      <div
        className="h-2 bg-gray-200 rounded-full cursor-pointer"
        onClick={e => {
          const rect = e.currentTarget.getBoundingClientRect()
          const pct = (e.clientX - rect.left) / rect.width
          seek(pct * duration)
        }}
      >
        <div
          className="h-full bg-blue-600 rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Transcript with sync */}
      {segments && segments.length > 0 && (
        <div className="max-h-96 overflow-y-auto space-y-1 border rounded-lg p-4">
          {segments.map((seg, idx) => (
            <div
              key={idx}
              onClick={() => seekToSegment(idx)}
              className={`flex gap-3 p-2 rounded cursor-pointer transition-colors ${
                idx === activeSegment
                  ? 'bg-blue-50 border-l-2 border-blue-500'
                  : 'hover:bg-gray-50'
              }`}
            >
              <span className="text-xs text-gray-400 tabular-nums whitespace-nowrap mt-0.5">
                {formatDuration(Math.floor(seg.start))}
              </span>
              <p className="text-sm text-gray-700">{seg.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
