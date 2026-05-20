import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import { FileText, Mail, Lock, User, ArrowRight, Loader2, Shield } from 'lucide-react'
import toast from 'react-hot-toast'

interface AuthPageProps {
  initialMode?: 'login' | 'register'
}

export function AuthPage({ initialMode = 'login' }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [inviteRequired, setInviteRequired] = useState(true)
  const { signIn, signUp, isLoading } = useAuthStore()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const fromUrl = params.get('invite')
    if (fromUrl) setInviteCode(fromUrl.toUpperCase())
    api.config.pilot().then((c) => setInviteRequired(c.invite_required)).catch(() => {})
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (mode === 'login') {
        await signIn(email, password)
        toast.success('Ласкаво просимо!')
      } else {
        if (inviteRequired && !inviteCode.trim()) {
          toast.error('Потрібен код запрошення')
          return
        }
        if (inviteCode.trim()) {
          const v = await api.invites.validate(inviteCode.trim())
          if (!v.valid) {
            toast.error(v.message || 'Невірний код')
            return
          }
        }
        await signUp(email, password, name)
        const token = useAuthStore.getState().token
        if (token && inviteCode.trim()) {
          await api.invites.claim(inviteCode.trim(), name)
        }
        toast.success('Акаунт створено!')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Помилка авторизації'
      toast.error(msg)
    }
  }

  return (
    <div className="min-h-screen bg-surface-0 dark:bg-surface-dark-0 flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-semibold text-gray-900 dark:text-white">DocMind OS</span>
        </div>

        <div className="card p-8">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-1">
            {mode === 'login' ? 'Вхід в систему' : 'Створити акаунт'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            {mode === 'login' ? 'AI-помічник для ваших документів' : 'Почніть безкоштовно вже сьогодні'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && inviteRequired && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Код запрошення
                </label>
                <input
                  className="input font-mono uppercase"
                  type="text"
                  placeholder="DM-XXXXXXXXXX"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  required
                />
              </div>
            )}

            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Ваше ім'я
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    className="input pl-9"
                    type="text"
                    placeholder="Іван Петренко"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    required
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  className="input pl-9"
                  type="email"
                  placeholder="ваш@email.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Пароль
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  className="input pl-9"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>
            </div>

            <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={isLoading}>
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              {mode === 'login' ? 'Увійти' : 'Створити акаунт'}
            </button>
          </form>

          {/* Security note */}
          <div className="mt-4 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
            <Shield className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Ваші дані зашифровані та ізольовані. Ніхто крім вас не має доступу.</span>
          </div>

          <div className="mt-5 pt-5 border-t border-surface-1 dark:border-surface-dark-3 text-center">
            <button
              type="button"
              className="text-sm text-brand-600 hover:text-brand-700 font-medium"
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            >
              {mode === 'login' ? 'Немає акаунту? Зареєструватись' : 'Вже є акаунт? Увійти'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
