import { useState } from 'react'
import { Shield, CheckCircle2, Lock, Eye, FileText, Settings, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

const TRUST_LEVELS = [
  {
    level: 1,
    name: 'Read Only',
    description: 'AI лише читає та відповідає на питання. Нічого не змінює.',
    icon: Eye,
    color: 'text-green-600',
    bg: 'bg-green-50 dark:bg-green-900/10',
    border: 'border-green-200 dark:border-green-800',
    features: ['Семантичний пошук по документах', 'Q&A з цитуванням джерел', 'Аналіз та підсумки'],
    recommended: true,
  },
  {
    level: 2,
    name: 'Suggest',
    description: 'AI пропонує дії, ви підтверджуєте кожну вручну.',
    icon: FileText,
    color: 'text-blue-600',
    bg: 'bg-blue-50 dark:bg-blue-900/10',
    border: 'border-blue-200 dark:border-blue-800',
    features: ['Всі можливості Рівня 1', 'Пропозиції структурування', 'Виявлення суперечностей'],
    recommended: false,
  },
  {
    level: 3,
    name: 'Supervised',
    description: 'AI діє самостійно, але кожна дія логується і може бути скасована.',
    icon: Settings,
    color: 'text-amber-600',
    bg: 'bg-amber-50 dark:bg-amber-900/10',
    border: 'border-amber-200 dark:border-amber-800',
    features: ['Всі можливості Рівня 2', 'Автоматична категоризація', 'Повний audit log', 'Rollback одним кліком'],
    recommended: false,
  },
]

export function SettingsPage() {
  const [activeLevel, setActiveLevel] = useState(1)
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 800))
    setSaving(false)
    toast.success(`Рівень безпеки ${activeLevel} збережено`)
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-brand-500" />
          Безпека та рівень AI
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Контролюйте що AI може робити з вашими документами
        </p>
      </div>

      {/* Data isolation notice */}
      <div className="card p-4 mb-6 flex items-start gap-3">
        <Lock className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Ваші дані повністю ізольовані</p>
          <p className="text-xs text-gray-500 mt-0.5">
            Документи зберігаються у вашому захищеному просторі. Жоден інший користувач не має доступу.
            Шифрування at-rest та in-transit.
          </p>
        </div>
      </div>

      {/* Trust Level Selection */}
      <div className="space-y-3 mb-6">
        {TRUST_LEVELS.map(tl => {
          const Icon = tl.icon
          const isActive = activeLevel === tl.level
          return (
            <button
              key={tl.level}
              onClick={() => setActiveLevel(tl.level)}
              className={`
                w-full text-left card p-4 transition-all duration-200
                ${isActive ? `${tl.border} border-2 ${tl.bg}` : 'hover:border-surface-3'}
              `}
            >
              <div className="flex items-start gap-4">
                <div className={`w-10 h-10 rounded-xl ${tl.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 ${tl.color}`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900 dark:text-white text-sm">
                      Рівень {tl.level} — {tl.name}
                    </span>
                    {tl.recommended && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 font-medium">
                        Рекомендовано
                      </span>
                    )}
                    {isActive && <CheckCircle2 className={`w-4 h-4 ml-auto ${tl.color}`} />}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{tl.description}</p>
                  <ul className="mt-2 space-y-1">
                    {tl.features.map(f => (
                      <li key={f} className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                        <CheckCircle2 className="w-3 h-3 text-green-400 flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* Rollback notice */}
      <div className="card p-4 mb-6 flex items-start gap-3 bg-surface-0 dark:bg-surface-dark-2">
        <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">Завжди можна відкотити</p>
          <p className="text-xs text-gray-500 mt-0.5">
            Будь-яка дія AI зберігається в audit log. Ви можете переглянути та скасувати будь-яку операцію
            в будь-який момент.
          </p>
        </div>
      </div>

      <button onClick={save} disabled={saving} className="btn-primary">
        {saving ? 'Збереження...' : 'Зберегти налаштування'}
      </button>
    </div>
  )
}
