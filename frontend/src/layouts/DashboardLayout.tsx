import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  FileText,
  MessageSquare,
  LogOut,
  Menu,
  Shield,
  ChevronRight,
  Moon,
  Sun,
  User,
  UserCog,
  Network,
} from 'lucide-react'
import type { MeResponse } from '@/lib/api'
import { ProfileSwitcher } from '@/components/ProfileSwitcher'
import { useAuthStore } from '@/stores/authStore'
import toast from 'react-hot-toast'

function ThemeToggle() {
  const [dark, setDark] = useState(false)
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])
  return (
    <button onClick={() => setDark(!dark)} className="btn-ghost p-2" type="button" aria-label="Toggle theme">
      {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  )
}

export function DashboardLayout({ me }: { me: MeResponse | null }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, signOut } = useAuthStore()

  const nav = [
    { path: '/documents', label: 'Документи', icon: FileText },
    { path: '/chat', label: 'Chat AI', icon: MessageSquare },
    { path: '/knowledge', label: 'Knowledge Graph', icon: Network },
    { path: '/settings', label: 'Безпека', icon: Shield },
    { path: '/profiles', label: 'Профілі AI', icon: User },
  ]
  if (me?.is_admin) {
    nav.push({ path: '/admin', label: 'Адмін', icon: UserCog })
  }

  const handleSignOut = async () => {
    await signOut()
    toast.success('До побачення!')
  }

  return (
    <div className="flex h-screen bg-surface-0 dark:bg-surface-dark-0 overflow-hidden">
      <aside
        className={`
        fixed inset-y-0 left-0 z-50 w-60 bg-white dark:bg-surface-dark-1
        border-r border-surface-2 dark:border-surface-dark-3
        flex flex-col transition-transform duration-300
        lg:relative lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}
      >
        <div className="flex items-center justify-between gap-2 px-5 py-5 border-b border-surface-1 dark:border-surface-dark-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white text-sm">Doc-Hub</span>
          </div>
          <ThemeToggle />
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-surface-1 dark:hover:bg-surface-dark-2'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {label}
                  {isActive && <ChevronRight className="w-3 h-3 ml-auto" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 pb-3 border-b border-surface-1 dark:border-surface-dark-3 mb-2">
          <ProfileSwitcher />
        </div>

        <div className="p-3 border-t border-surface-1 dark:border-surface-dark-3">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
              <span className="text-brand-700 dark:text-brand-400 text-xs font-semibold">
                {user?.email?.[0]?.toUpperCase() ?? 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 dark:text-white truncate">{user?.email}</p>
              <p className="text-xs text-gray-400">{me?.is_admin ? 'Адміністратор' : 'Пілот'}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            type="button"
            className="mt-1 w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500
                       hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Вийти
          </button>
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-surface-2 dark:border-surface-dark-3">
          <button onClick={() => setSidebarOpen(true)} className="btn-ghost p-2" type="button">
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-semibold text-sm text-gray-900 dark:text-white flex-1">Doc-Hub</span>
          <ThemeToggle />
        </div>

        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
