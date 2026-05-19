import { useEffect, useState } from 'react'
import { useProfileStore } from '@/stores/profileStore'
import { Plus, Trash2, Check, BookOpen, Briefcase, Scale, Wrench, Heart, User } from 'lucide-react'
import toast from 'react-hot-toast'

const DOMAINS = [
  { value: 'education', label: 'Освіта', icon: BookOpen, desc: 'Школярі, студенти, ЗНО' },
  { value: 'legal', label: 'Право', icon: Scale, desc: 'Юристи, договори' },
  { value: 'business', label: 'Бізнес', icon: Briefcase, desc: 'Менеджери, бухгалтери' },
  { value: 'technical', label: 'Техніка', icon: Wrench, desc: 'Технічна документація' },
  { value: 'medical', label: 'Медицина', icon: Heart, desc: 'Медичні документи' },
  { value: 'general', label: 'Загальний', icon: User, desc: 'Універсальний' },
]

const COMPLEXITY_LABELS = ['', 'Базовий (5-6 кл)', 'Простий (7-9 кл)', 'Середній', 'Просунутий', 'Експерт']
const COMPLEXITY_COLORS = [
  '',
  'bg-green-100 text-green-700',
  'bg-teal-100 text-teal-700',
  'bg-blue-100 text-blue-700',
  'bg-violet-100 text-violet-700',
  'bg-orange-100 text-orange-700',
]

export function ProfilesPage() {
  const { profiles, activeProfile, fetch, activate, create, remove } = useProfileStore()
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', domain: 'general', complexity_level: 3 })

  useEffect(() => {
    fetch()
  }, [fetch])

  const handleCreate = async () => {
    if (!form.name.trim()) {
      toast.error('Введіть назву профілю')
      return
    }
    try {
      await create({
        name: form.name,
        domain: form.domain,
        complexity_level: form.complexity_level,
        preferences: {
          response_style: 'balanced',
          language: 'uk',
          forbidden_topics: [],
          temperature: 0.3,
        },
      })
      setCreating(false)
      setForm({ name: '', domain: 'general', complexity_level: 3 })
      toast.success('Профіль створено!')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Помилка')
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Профілі AI</h1>
          <p className="text-sm text-gray-500 mt-0.5">Налаштуй AI під кожну задачу</p>
        </div>
        <button type="button" onClick={() => setCreating(true)} className="btn-primary">
          <Plus className="w-4 h-4" /> Новий профіль
        </button>
      </div>

      {creating && (
        <div className="card p-5 mb-5 animate-slide-up">
          <h2 className="font-medium text-gray-900 dark:text-white mb-4">Новий профіль</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Назва профілю
              </label>
              <input
                className="input"
                placeholder="Напр: 10 клас Алгебра, Юридичний режим"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Галузь
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {DOMAINS.map((d) => {
                  const Icon = d.icon
                  return (
                    <button
                      key={d.value}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, domain: d.value }))}
                      className={`flex items-center gap-2 p-2.5 rounded-lg border text-left transition-all
                                  ${form.domain === d.value
                                    ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20'
                                    : 'border-surface-2 dark:border-surface-dark-3 hover:border-brand-200'}`}
                    >
                      <Icon
                        className={`w-4 h-4 flex-shrink-0 ${form.domain === d.value ? 'text-brand-600' : 'text-gray-400'}`}
                      />
                      <div>
                        <p className="text-xs font-medium text-gray-900 dark:text-white">{d.label}</p>
                        <p className="text-xs text-gray-400">{d.desc}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Рівень складності:{' '}
                <span className="text-brand-600">{COMPLEXITY_LABELS[form.complexity_level]}</span>
              </label>
              <input
                type="range"
                min={1}
                max={5}
                value={form.complexity_level}
                onChange={(e) => setForm((f) => ({ ...f, complexity_level: +e.target.value }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>1 — Базовий</span>
                <span>3 — Середній</span>
                <span>5 — Експерт</span>
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button type="button" onClick={handleCreate} className="btn-primary">
                Створити
              </button>
              <button type="button" onClick={() => setCreating(false)} className="btn-ghost">
                Скасувати
              </button>
            </div>
          </div>
        </div>
      )}

      {profiles.length === 0 && !creating ? (
        <div className="card p-12 text-center">
          <User className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Ще немає профілів. Створіть перший!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {profiles.map((p) => {
            const Icon = DOMAINS.find((d) => d.value === p.domain)?.icon ?? User
            const isActive = p.id === activeProfile?.id
            return (
              <div
                key={p.id}
                className={`card p-4 flex items-center gap-4 transition-all
                ${isActive ? 'ring-2 ring-brand-400' : ''}`}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
                                ${isActive ? 'bg-brand-100 dark:bg-brand-900/30' : 'bg-surface-1 dark:bg-surface-dark-2'}`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-brand-600' : 'text-gray-400'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900 dark:text-white text-sm">{p.name}</p>
                    {isActive && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400">
                        Активний
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${COMPLEXITY_COLORS[p.complexity_level]}`}
                    >
                      {COMPLEXITY_LABELS[p.complexity_level]}
                    </span>
                    <span className="text-xs text-gray-400">
                      {DOMAINS.find((d) => d.value === p.domain)?.label}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {!isActive && (
                    <button
                      type="button"
                      onClick={() => {
                        activate(p.id)
                        toast.success(`Активовано: ${p.name}`)
                      }}
                      className="btn-ghost text-xs py-1.5 px-3"
                    >
                      <Check className="w-3.5 h-3.5" /> Активувати
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      remove(p.id)
                      toast.success('Профіль видалено')
                    }}
                    className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/10 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
