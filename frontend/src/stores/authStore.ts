import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { supabase } from '@/lib/supabase'

interface User {
  id: string
  email: string
  user_metadata?: Record<string, unknown>
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, name: string) => Promise<void>
  signOut: () => Promise<void>
  refreshToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoading: false,

      signIn: async (email, password) => {
        set({ isLoading: true })
        const { data, error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) { set({ isLoading: false }); throw error }
        set({
          user: data.user as User,
          token: data.session?.access_token ?? null,
          isLoading: false,
        })
      },

      signUp: async (email, password, name) => {
        set({ isLoading: true })
        const { data, error } = await supabase.auth.signUp({
          email, password,
          options: { data: { full_name: name } }
        })
        if (error) { set({ isLoading: false }); throw error }
        set({
          user: data.user as User,
          token: data.session?.access_token ?? null,
          isLoading: false,
        })
      },

      signOut: async () => {
        await supabase.auth.signOut()
        set({ user: null, token: null })
      },

      refreshToken: async () => {
        const { data } = await supabase.auth.getSession()
        if (data.session) {
          set({ token: data.session.access_token, user: data.session.user as User })
        }
      },
    }),
    { name: 'docmind-auth', partialize: (s) => ({ user: s.user, token: s.token }) }
  )
)
