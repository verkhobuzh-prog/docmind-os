import { useEffect, type ComponentType } from 'react'
import { useProfileStore } from '@/stores/profileStore'
import { ChevronDown, User, BookOpen, Briefcase, Scale, Wrench, Heart } from 'lucide-react'

const DOMAIN_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  education: BookOpen,
  legal: Scale,
  business: Briefcase,
  technical: Wrench,
  medical: Heart,
  general: User,
}

const LEVEL_LABELS = ['', 'Базовий', 'Простий', 'Середній', 'Просунутий', 'Експерт']
const LEVEL_COLORS = ['', 'text-green-500', 'text-teal-500', 'text-blue-500', 'text-violet-500', 'text-orange-500']

export function ProfileSwitcher() {
  const { profiles, activeProfile, fetch, activate } = useProfileStore()

  useEffect(() => {
    fetch()
  }, [fetch])

  if (!profiles.length) return null

  const Icon = DOMAIN_ICONS[activeProfile?.domain ?? 'general'] ?? User

  return (
    <div className="relative group">
      <button
        type="button"
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
                         hover:bg-surface-1 dark:hover:bg-surface-dark-2 transition-all"
      >
        <div className="w-6 h-6 rounded-md bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center flex-shrink-0">
          <Icon className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
        </div>
        <div className="flex-1 text-left min-w-0">
          <p className="text-xs font-medium text-gray-900 dark:text-white truncate">
            {activeProfile?.name ?? 'Оберіть профіль'}
          </p>
          {activeProfile && (
            <p className={`text-xs ${LEVEL_COLORS[activeProfile.complexity_level]}`}>
              {LEVEL_LABELS[activeProfile.complexity_level]}
            </p>
          )}
        </div>
        <ChevronDown className="w-3 h-3 text-gray-400 flex-shrink-0" />
      </button>

      <div
        className="absolute bottom-full left-0 right-0 mb-1 hidden group-focus-within:block
                      bg-white dark:bg-surface-dark-1 border border-surface-2 dark:border-surface-dark-3
                      rounded-xl shadow-lg overflow-hidden z-50"
      >
        {profiles.map((p) => {
          const PIcon = DOMAIN_ICONS[p.domain] ?? User
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => activate(p.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-sm transition-colors
                          ${p.is_active
                            ? 'bg-brand-50 dark:bg-brand-900/20'
                            : 'hover:bg-surface-1 dark:hover:bg-surface-dark-2'}`}
            >
              <PIcon className={`w-4 h-4 flex-shrink-0 ${p.is_active ? 'text-brand-600' : 'text-gray-400'}`} />
              <div className="flex-1 text-left">
                <p
                  className={`text-xs font-medium ${p.is_active ? 'text-brand-700 dark:text-brand-400' : 'text-gray-700 dark:text-gray-300'}`}
                >
                  {p.name}
                </p>
                <p className={`text-xs ${LEVEL_COLORS[p.complexity_level]}`}>
                  {LEVEL_LABELS[p.complexity_level]} · {p.domain}
                </p>
              </div>
              {p.is_active && (
                <div className="w-1.5 h-1.5 rounded-full bg-brand-500 flex-shrink-0" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
