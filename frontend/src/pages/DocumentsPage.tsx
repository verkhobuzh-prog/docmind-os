import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Document } from '@/lib/api'
import {
  Upload, FileText, File, Loader2, CheckCircle2, XCircle,
  Clock, RefreshCw, Trash2, Plus, AlertCircle
} from 'lucide-react'
import toast from 'react-hot-toast'
import { formatBytes, formatDate } from '@/lib/utils'

const STATUS_CONFIG = {
  uploaded: { label: 'Завантажено',  color: 'text-blue-600 bg-blue-50',   icon: Clock },
  parsing:  { label: 'Обробляється', color: 'text-amber-600 bg-amber-50', icon: Loader2 },
  indexed:  { label: 'Готово',       color: 'text-green-600 bg-green-50', icon: CheckCircle2 },
  failed:   { label: 'Помилка',      color: 'text-red-600 bg-red-50',     icon: XCircle },
}

export function DocumentsPage() {
  const qc = useQueryClient()
  const [uploading, setUploading] = useState(false)

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: api.documents.list,
    refetchInterval: (query) => {
      const hasProcessing = query.state.data?.some(d => d.status === 'parsing')
      return hasProcessing ? 3000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      for (const file of files) {
        await api.documents.upload(file)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Документи завантажено та передано на обробку')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const ingestMutation = useMutation({
    mutationFn: api.documents.ingest,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Переіндексацію запущено')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: api.documents.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Документ видалено')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return
    setUploading(true)
    await uploadMutation.mutateAsync(accepted)
    setUploading(false)
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'], 'text/markdown': ['.md'],
              'application/vnd.ms-excel': ['.xls'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxSize: 50 * 1024 * 1024,
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Документи</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {docs.length} документ{docs.length === 1 ? '' : 'ів'} у базі
          </p>
        </div>
      </div>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`
          card p-8 text-center cursor-pointer mb-6 transition-all duration-200
          border-2 border-dashed
          ${isDragActive
            ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/10'
            : 'border-surface-2 dark:border-surface-dark-3 hover:border-brand-300 hover:bg-brand-50/50 dark:hover:bg-brand-900/5'}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          {uploading ? (
            <Loader2 className="w-10 h-10 text-brand-500 animate-spin" />
          ) : (
            <div className="w-12 h-12 rounded-xl bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center">
              <Upload className="w-6 h-6 text-brand-600 dark:text-brand-400" />
            </div>
          )}
          <div>
            <p className="font-medium text-gray-900 dark:text-white text-sm">
              {uploading ? 'Завантаження...' : isDragActive ? 'Відпустіть файли' : 'Перетягніть файли сюди'}
            </p>
            <p className="text-xs text-gray-400 mt-1">PDF, TXT, MD, XLSX — до 50MB</p>
          </div>
          {!uploading && (
            <button type="button" className="btn-primary text-xs px-3 py-1.5">
              <Plus className="w-3.5 h-3.5" />
              Вибрати файли
            </button>
          )}
        </div>
      </div>

      {uploadMutation.isError && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/30 dark:bg-red-900/10 dark:text-red-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {(uploadMutation.error as Error).message}
        </div>
      )}

      {/* Documents List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
        </div>
      ) : docs.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Ще немає документів. Завантажте перший!</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-1 dark:border-surface-dark-3">
                <th className="text-left text-xs font-medium text-gray-400 px-5 py-3">Документ</th>
                <th className="text-left text-xs font-medium text-gray-400 px-5 py-3 hidden md:table-cell">Розмір</th>
                <th className="text-left text-xs font-medium text-gray-400 px-5 py-3 hidden md:table-cell">Дата</th>
                <th className="text-left text-xs font-medium text-gray-400 px-5 py-3">Статус</th>
                <th className="px-5 py-3 w-16" />
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-1 dark:divide-surface-dark-3">
              {docs.map((doc: Document) => {
                const cfg = STATUS_CONFIG[doc.status] ?? STATUS_CONFIG.uploaded
                const StatusIcon = cfg.icon
                return (
                  <tr key={doc.id} className="hover:bg-surface-0 dark:hover:bg-surface-dark-2/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <File className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">
                          {doc.filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 hidden md:table-cell">
                      <span className="text-xs text-gray-400">{formatBytes(doc.size_bytes)}</span>
                    </td>
                    <td className="px-5 py-3.5 hidden md:table-cell">
                      <span className="text-xs text-gray-400">{formatDate(doc.created_at)}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${cfg.color}`}>
                        <StatusIcon className={`w-3 h-3 ${doc.status === 'parsing' ? 'animate-spin' : ''}`} />
                        {cfg.label}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1">
                        {doc.status === 'failed' && (
                          <button
                            onClick={() => ingestMutation.mutate(doc.id)}
                            className="p-1.5 rounded hover:bg-surface-1 dark:hover:bg-surface-dark-2 text-gray-400 hover:text-brand-600"
                            title="Переіндексувати"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => deleteMutation.mutate(doc.id)}
                          className="p-1.5 rounded hover:bg-surface-1 dark:hover:bg-surface-dark-2 text-gray-400 hover:text-red-600"
                          title="Видалити"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
