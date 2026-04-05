import { useEffect, useState, useRef } from 'react'
import { Upload, FileText, Trash2, Star } from 'lucide-react'
import {
  fetchScripts, createScript, updateScript, deleteScript,
  type SalesScript,
} from '../api/client'
import { formatDate } from '../lib/utils'

export default function Scripts() {
  const [scripts, setScripts] = useState<SalesScript[]>([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [selected, setSelected] = useState<SalesScript | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadName, setUploadName] = useState('')
  const [uploadDesc, setUploadDesc] = useState('')
  const [uploading, setUploading] = useState(false)

  const load = () => {
    setLoading(true)
    fetchScripts().then(setScripts).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file && !uploadName) return

    setUploading(true)
    const formData = new FormData()
    formData.append('name', uploadName || file?.name || 'Скрипт')
    if (uploadDesc) formData.append('description', uploadDesc)
    if (file) formData.append('file', file)
    if (!file) formData.append('content', 'Текст скрипта')

    try {
      await createScript(formData)
      load()
      setShowUpload(false)
      setUploadName('')
      setUploadDesc('')
    } finally {
      setUploading(false)
    }
  }

  const handleActivate = async (script: SalesScript) => {
    await updateScript(script.id, { is_active: !script.is_active })
    load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить скрипт?')) return
    await deleteScript(id)
    if (selected?.id === id) setSelected(null)
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Скрипты продаж</h1>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          <Upload size={16} />
          Загрузить скрипт
        </button>
      </div>

      {/* Upload form */}
      {showUpload && (
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h2 className="font-semibold">Новый скрипт</h2>
          <input
            type="text"
            placeholder="Название скрипта"
            value={uploadName}
            onChange={e => setUploadName(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Описание (опционально)"
            value={uploadDesc}
            onChange={e => setUploadDesc(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          />
          <div className="flex items-center gap-4">
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.pdf,.docx,.doc"
              className="text-sm"
            />
            <span className="text-xs text-gray-400">PDF, DOCX, TXT</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleUpload}
              disabled={uploading || !uploadName}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50"
            >
              {uploading ? 'Загрузка...' : 'Загрузить'}
            </button>
            <button
              onClick={() => setShowUpload(false)}
              className="px-4 py-2 border rounded-lg text-sm"
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Scripts list */}
        <div className="space-y-3">
          {loading ? (
            <p className="text-gray-400">Загрузка...</p>
          ) : scripts.length === 0 ? (
            <p className="text-gray-400 text-center py-12">Нет загруженных скриптов</p>
          ) : (
            scripts.map(script => (
              <div
                key={script.id}
                onClick={() => setSelected(script)}
                className={`bg-white rounded-xl border p-4 cursor-pointer transition-shadow hover:shadow-md ${
                  selected?.id === script.id ? 'ring-2 ring-blue-500' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FileText size={18} className="text-gray-400" />
                    <div>
                      <h3 className="font-medium text-sm">{script.name}</h3>
                      {script.description && (
                        <p className="text-xs text-gray-500 mt-0.5">{script.description}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={e => { e.stopPropagation(); handleActivate(script) }}
                      className={`p-1.5 rounded-lg ${script.is_active ? 'text-yellow-500' : 'text-gray-300 hover:text-yellow-500'}`}
                      title={script.is_active ? 'Активный скрипт' : 'Сделать активным'}
                    >
                      <Star size={16} fill={script.is_active ? 'currentColor' : 'none'} />
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(script.id) }}
                      className="p-1.5 text-gray-300 hover:text-red-500 rounded-lg"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  {script.original_file && <span>{script.original_file}</span>}
                  {script.file_type && <span className="uppercase">{script.file_type}</span>}
                  {script.created_at && <span>{formatDate(script.created_at)}</span>}
                  {script.is_active && (
                    <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                      Активный
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Script preview */}
        <div className="bg-white rounded-xl border p-6">
          {selected ? (
            <>
              <h2 className="font-semibold mb-3">{selected.name}</h2>
              <div className="max-h-[600px] overflow-y-auto">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                  {selected.content}
                </pre>
              </div>
            </>
          ) : (
            <p className="text-gray-400 text-center py-12">Выберите скрипт для просмотра</p>
          )}
        </div>
      </div>
    </div>
  )
}
