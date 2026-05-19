import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type InviteCode, type PilotMember } from '@/lib/api'
import { Copy, Loader2, Plus, Users } from 'lucide-react'
import toast from 'react-hot-toast'

export function AdminPilotPage() {
  const qc = useQueryClient()
  const [label, setLabel] = useState('')
  const [maxUses, setMaxUses] = useState(10)

  const { data: invites = [], isLoading: loadingInvites } = useQuery({
    queryKey: ['admin-invites'],
    queryFn: api.admin.listInvites,
  })

  const { data: members = [], isLoading: loadingMembers } = useQuery({
    queryKey: ['admin-members'],
    queryFn: api.admin.listMembers,
  })

  const createMutation = useMutation({
    mutationFn: () => api.admin.createInvite({ label: label || undefined, max_uses: maxUses }),
    onSuccess: (inv) => {
      qc.invalidateQueries({ queryKey: ['admin-invites'] })
      toast.success('Запрошення створено')
      if (inv.invite_url) {
        navigator.clipboard.writeText(inv.invite_url)
        toast.success('Посилання скопійовано')
      }
      setLabel('')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const copy = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Скопійовано')
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Адмін пілоту</h1>
        <p className="text-sm text-gray-500 mt-1">Запрошення та учасники</p>
      </div>

      <section className="card p-5 space-y-4">
        <h2 className="text-sm font-medium flex items-center gap-2">
          <Plus className="w-4 h-4" /> Нове запрошення
        </h2>
        <div className="grid sm:grid-cols-3 gap-3">
          <input
            className="input sm:col-span-2"
            placeholder="Мітка (напр. Група Івана)"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
          <input
            className="input"
            type="number"
            min={1}
            max={500}
            value={maxUses}
            onChange={(e) => setMaxUses(+e.target.value)}
          />
        </div>
        <button
          type="button"
          className="btn-primary"
          disabled={createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Створити'}
        </button>
      </section>

      <section className="card overflow-hidden">
        <h2 className="text-sm font-medium px-5 py-3 border-b border-surface-1 dark:border-surface-dark-3">
          Активні коди
        </h2>
        {loadingInvites ? (
          <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-brand-500" /></div>
        ) : (
          <ul className="divide-y divide-surface-1 dark:divide-surface-dark-3">
            {invites.map((inv: InviteCode) => (
              <li key={inv.id} className="px-5 py-3 flex flex-wrap items-center gap-2 text-sm">
                <code className="font-mono text-brand-700 dark:text-brand-400">{inv.code}</code>
                {inv.label && <span className="text-gray-500">— {inv.label}</span>}
                <span className="text-xs text-gray-400">
                  {inv.use_count}/{inv.max_uses}
                </span>
                {inv.invite_url && (
                  <button type="button" className="btn-ghost p-1 ml-auto" onClick={() => copy(inv.invite_url!)}>
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card overflow-hidden">
        <h2 className="text-sm font-medium px-5 py-3 border-b border-surface-1 dark:border-surface-dark-3 flex items-center gap-2">
          <Users className="w-4 h-4" /> Хто підключився ({members.length})
        </h2>
        {loadingMembers ? (
          <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-brand-500" /></div>
        ) : members.length === 0 ? (
          <p className="p-6 text-sm text-gray-500 text-center">Ще ніхто не приєднався</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-surface-1 dark:border-surface-dark-3">
                <th className="px-5 py-2">Email</th>
                <th className="px-5 py-2 hidden sm:table-cell">Ім&apos;я</th>
                <th className="px-5 py-2">Код</th>
                <th className="px-5 py-2 hidden md:table-cell">Дата</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-1 dark:divide-surface-dark-3">
              {members.map((m: PilotMember) => (
                <tr key={m.id}>
                  <td className="px-5 py-2.5">{m.email}</td>
                  <td className="px-5 py-2.5 hidden sm:table-cell text-gray-500">{m.display_name || '—'}</td>
                  <td className="px-5 py-2.5 font-mono text-xs">{m.invite_code || '—'}</td>
                  <td className="px-5 py-2.5 hidden md:table-cell text-gray-400 text-xs">
                    {new Date(m.joined_at).toLocaleString('uk-UA')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
