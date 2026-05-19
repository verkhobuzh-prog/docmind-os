import { useEffect, useState } from 'react'
import { FileText, MessageSquare, LogOut, Menu, Shield, ChevronRight, Moon, Sun, User } from 'lucide-react'
import { ProfileSwitcher } from '@/components/ProfileSwitcher'
import { useAuthStore } from '@/stores/authStore'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ProfilesPage } from '@/pages/ProfilesPage'
import toast from 'react-hot-toast'

type Page = 'documents' | 'chat' | 'settings' | 'profiles'

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

export function DashboardLayout() {
  const [page, setPage] = useState<Page>('documents')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, signOut } = useAuthStore()

  const nav = [
    { id: 'documents' as Page, label: 'Документи', icon: FileText },
    { id: 'chat'      as Page, label: 'Chat AI',   icon: MessageSquare },
    { id: 'settings'  as Page, label: 'Безпека',   icon: Shield },
    { id: 'profiles'  as Page, label: 'Профілі AI', icon: User },
  ]

  const handleSignOut = async () => {
    await signOut()
    toast.success('До побачення!')
  }

  return (
    <div className="flex h-screen bg-surface-0 dark:bg-surface-dark-0 overflow-hidden">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-60 bg-white dark:bg-surface-dark-1
        border-r border-surface-2 dark:border-surface-dark-3
        flex flex-col transition-transform duration-300
        lg:relative lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo */}
        <div className="flex items-center justify-between gap-2 px-5 py-5 border-b border-surface-1 dark:border-surface-dark-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white text-sm">DocMind OS</span>
          </div>
          <ThemeToggle />
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => { setPage(id); setSidebarOpen(false) }}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                ${page === id
                  ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-surface-1 dark:hover:bg-surface-dark-2'}
              `}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
              {page === id && <ChevronRight className="w-3 h-3 ml-auto" />}
            </button>
          ))}
        </nav>

        <div className="px-3 pb-3 border-b border-surface-1 dark:border-surface-dark-3 mb-2">
          <ProfileSwitcher />
        </div>

        {/* User */}
        <div className="p-3 border-t border-surface-1 dark:border-surface-dark-3">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
              <span className="text-brand-700 dark:text-brand-400 text-xs font-semibold">
                {user?.email?.[0]?.toUpperCase() ?? 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 dark:text-white truncate">{user?.email}</p>
              <p className="text-xs text-gray-400">Рівень 1 — Read Only</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            className="mt-1 w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500
                       hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Вийти
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile topbar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-surface-2 dark:border-surface-dark-3">
          <button onClick={() => setSidebarOpen(true)} className="btn-ghost p-2" type="button">
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-semibold text-sm text-gray-900 dark:text-white flex-1">DocMind OS</span>
          <ThemeToggle />
        </div>

        <div className="flex-1 overflow-auto">
          {page === 'documents' && <DocumentsPage />}
          {page === 'chat'      && <ChatPage />}
          {page === 'settings'  && <SettingsPage />}
          {page === 'profiles'  && <ProfilesPage />}
        </div>
      </main>
    </div>
  )
}
