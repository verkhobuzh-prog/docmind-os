import { useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { AuthPage } from '@/pages/AuthPage'
import { DashboardLayout } from '@/layouts/DashboardLayout'
import { Toaster } from 'react-hot-toast'

export default function App() {
  const { user, refreshToken } = useAuthStore()

  useEffect(() => {
    refreshToken()
  }, [])

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'font-sans text-sm',
          style: { borderRadius: '10px', padding: '12px 16px' },
        }}
      />
      {user ? <DashboardLayout /> : <AuthPage />}
    </>
  )
}
