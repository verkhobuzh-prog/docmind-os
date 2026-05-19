import { useState } from 'react'
import { KeyRound, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'

export function InviteGatePage() {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const { refreshToken } = useAuthStore()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code.trim()) return
    setLoading(true)
    try {
      await api.invites.claim(code.trim())
      toast.success('Запрошення прийнято!')
      await refreshToken()
      window.location.reload()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Помилка')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-surface-0 dark:bg-surface-dark-0">
      <div className="card p-8 max-w-md w-full">
        <div className="flex items-center gap-2 mb-4">
          <KeyRound className="w-5 h-5 text-brand-600" />
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Код запрошення</h1>
        </div>
        <p className="text-sm text-gray-500 mb-6">
          Пілот доступний лише за запрошенням. Введіть код від адміністратора.
        </p>
        <form onSubmit={submit} className="space-y-4">
          <input
            className="input font-mono uppercase"
            placeholder="DM-XXXXXXXXXX"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          <button type="submit" className="btn-primary w-full justify-center" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Підтвердити'}
          </button>
        </form>
      </div>
    </div>
  )
}
