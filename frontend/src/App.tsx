import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { AuthPage } from '@/pages/AuthPage'
import { DashboardLayout } from '@/layouts/DashboardLayout'
import { InviteGatePage } from '@/pages/InviteGatePage'
import { KnowledgePage } from '@/pages/KnowledgePage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ProfilesPage } from '@/pages/ProfilesPage'
import { AdminPilotPage } from '@/pages/AdminPilotPage'
import { Toaster } from 'react-hot-toast'
import { api, type MeResponse } from '@/lib/api'
import { Loader2 } from 'lucide-react'

export default function App() {
  const { user, token, refreshToken } = useAuthStore()
  const [me, setMe] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    refreshToken()
  }, [refreshToken])

  useEffect(() => {
    if (!user || !token) {
      setMe(null)
      return
    }
    let cancelled = false
    setLoading(true)
    api.auth
      .me()
      .then((data) => {
        if (!cancelled) setMe(data)
      })
      .catch(() => {
        if (!cancelled) setMe({ id: user.id, email: user.email, is_admin: false, pilot_member: false })
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user, token])

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'font-sans text-sm',
          style: { borderRadius: '10px', padding: '12px 16px' },
        }}
      />
      {!user ? (
        <AuthPage />
      ) : loading ? (
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
        </div>
      ) : me && !me.pilot_member && !me.is_admin ? (
        <InviteGatePage />
      ) : (
        <BrowserRouter>
          <Routes>
            <Route element={<DashboardLayout me={me} />}>
              <Route index element={<Navigate to="/documents" replace />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="knowledge" element={<KnowledgePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="profiles" element={<ProfilesPage />} />
              {me?.is_admin && <Route path="admin" element={<AdminPilotPage />} />}
            </Route>
          </Routes>
        </BrowserRouter>
      )}
    </>
  )
}
