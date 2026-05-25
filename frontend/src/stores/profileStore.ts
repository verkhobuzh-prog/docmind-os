import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '@/lib/api'

export interface ProfilePreferences {
  response_style: 'concise' | 'balanced' | 'detailed'
  language: string
  forbidden_topics: string[]
  temperature: number
}

export interface UserProfile {
  id: string
  name: string
  complexity_level: number
  domain: string
  is_active: boolean
  preferences: ProfilePreferences
  created_at: string
}

interface ProfileState {
  profiles: UserProfile[]
  activeProfile: UserProfile | null
  isLoading: boolean
  fetch: () => Promise<void>
  activate: (profileId: string) => Promise<void>
  create: (data: Omit<UserProfile, 'id' | 'is_active' | 'created_at'>) => Promise<void>
  remove: (profileId: string) => Promise<void>
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      profiles: [],
      activeProfile: null,
      isLoading: false,

      fetch: async () => {
        set({ isLoading: true })
        try {
          const profiles = await api.profiles.list()
          const active = profiles.find((p) => p.is_active) ?? null
          set({ profiles, activeProfile: active })
        } finally {
          set({ isLoading: false })
        }
      },

      activate: async (profileId) => {
        const profile = await api.profiles.activate(profileId)
        set((state) => ({
          profiles: state.profiles.map((p) => ({ ...p, is_active: p.id === profileId })),
          activeProfile: profile,
        }))
      },

      create: async (data) => {
        const profile = await api.profiles.create(data)
        set((state) => ({
          profiles: [...state.profiles, profile],
          activeProfile: profile.is_active ? profile : state.activeProfile,
        }))
      },

      remove: async (profileId) => {
        await api.profiles.delete(profileId)
        set((state) => ({
          profiles: state.profiles.filter((p) => p.id !== profileId),
          activeProfile: state.activeProfile?.id === profileId ? null : state.activeProfile,
        }))
      },
    }),
    { name: 'dochub-profiles', partialize: (s) => ({ activeProfile: s.activeProfile }) }
  )
)
