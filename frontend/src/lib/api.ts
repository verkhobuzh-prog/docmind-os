import { useAuthStore } from '@/stores/authStore'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function publicRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'API error')
  }
  return res.json()
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().token
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.body && !(init.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...init.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.error ?? err.detail ?? 'API error')
  }
  if (res.status === 204) return null as T
  return res.json()
}

// --- Types ---
export interface Document {
  id: string
  filename: string
  status: 'uploaded' | 'parsing' | 'indexed' | 'failed'
  size_bytes: number
  created_at: string
  subject?: string | null
  document_type?: string | null
  mime_type?: string | null
  metadata?: Record<string, unknown>
}

export interface MeResponse {
  id: string
  email?: string
  role?: string
  is_admin: boolean
  pilot_member: boolean
}

export interface InviteCode {
  id: string
  code: string
  label?: string | null
  max_uses: number
  use_count: number
  invite_url?: string | null
  created_at: string
}

export interface PilotMember {
  id: string
  email: string
  display_name?: string | null
  invite_code?: string | null
  joined_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ chunk_id: string; content: string; similarity: number }>
  citations?: string[]
  risk_score?: number
  risk_level?: string
  risk_warning?: string | null
}

export interface ChatResponse {
  answer: string
  sources: Array<{ chunk_id: string; content: string; similarity: number }>
  citations: string[]
  model?: string
  risk_score?: number
  risk_level?: string
  risk_warning?: string | null
  low_confidence_facts?: number
  disputed_facts?: number
  total_facts_analyzed?: number
}

export interface RiskAnalysisResponse {
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical' | string
  explanation: string
  low_confidence_triples: number
  disputed_triples: number
  total_triples: number
  analyzed_documents: number
}

export interface ReasoningFinding {
  finding_type: string
  severity: string
  title: string
  description: string
  entities_involved: string[]
  doc_ids_involved: string[]
  evidence: string[]
  confidence: number
  recommendation: string
}

export interface DocumentAnalysisResponse {
  doc_id: string
  findings: ReasoningFinding[]
  total_findings: number
  risk_score: number
  analyzed_at: string
}

export interface CompareDocumentsResponse {
  documents_analyzed: number
  common_entities: string[]
  contradictions: ReasoningFinding[]
  risk_score: number
  summary: string
}

export interface KnowledgeGraphNode {
  id: string
  name: string
  type: string
}

export interface KnowledgeGraphEdge {
  source: string
  target: string
  type: string
  confidence?: number | null
}

export interface KnowledgeEntityGraph {
  entity: string
  depth: number
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  total_nodes: number
  total_edges: number
}

export interface KnowledgeStats {
  total_triples_in_db: number
  graph_enabled: boolean
  triple_extraction_enabled: boolean
}

export interface ConfidenceSummary {
  total_triples: number
  avg_confidence: number
  high_confidence: number
  medium_confidence: number
  low_confidence: number
  disputed: number
}

export interface ProvenanceSource {
  id: string
  evidence_quote: string | null
  doc_id: string
  confidence: number
  validation_status: string
}

export interface UserProfile {
  id: string
  name: string
  complexity_level: number
  domain: string
  is_active: boolean
  preferences: {
    response_style: 'concise' | 'balanced' | 'detailed'
    language: string
    forbidden_topics: string[]
    temperature: number
  }
  created_at: string
}

// --- Documents ---
export const api = {
  health: () => request<{ status: string; checks: Record<string, string> }>('/health'),

  documents: {
    list: async () => {
      const res = await request<{ items: Document[]; total: number }>('/api/v1/documents')
      return res.items
    },
    get: (id: string) => request<Document>(`/api/v1/documents/${id}`),
    upload: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const res = await request<{ document: Document }>('/api/v1/documents/upload', {
        method: 'POST',
        body: fd,
      })
      return res.document
    },
    ingest: (id: string) =>
      request<{ message: string }>(`/api/v1/documents/${id}/ingest`, { method: 'POST' }),
    delete: (id: string) =>
      request<null>(`/api/v1/documents/${id}`, { method: 'DELETE' }),
  },

  chat: {
    query: (query: string, topK = 8, documentIds?: string[]) =>
      request<ChatResponse>('/api/v1/chat', {
        method: 'POST',
        body: JSON.stringify({ query, top_k: topK, document_ids: documentIds }),
      }),

    stream: async function* (query: string, topK = 8) {
      const token = useAuthStore.getState().token
      const res = await fetch(`${BASE}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ query, top_k: topK, stream: true }),
      })
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) return
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        yield decoder.decode(value, { stream: true })
      }
    },
  },

  config: {
    pilot: () =>
      publicRequest<{ invite_required: boolean; frontend_url: string }>('/api/v1/config/pilot'),
  },

  invites: {
    validate: (code: string) =>
      publicRequest<{ valid: boolean; message?: string }>('/api/v1/invites/validate', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
    claim: (code: string, display_name?: string) =>
      request<{ ok: boolean; message: string }>('/api/v1/invites/claim', {
        method: 'POST',
        body: JSON.stringify({ code, display_name }),
      }),
  },

  admin: {
    listInvites: () => request<InviteCode[]>('/api/v1/admin/invites'),
    listMembers: () => request<PilotMember[]>('/api/v1/admin/members'),
    createInvite: (data: { label?: string; max_uses?: number; expires_in_days?: number }) =>
      request<InviteCode>('/api/v1/admin/invites', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  auth: {
    me: () => request<MeResponse>('/api/v1/auth/me'),
  },

  knowledge: {
    entityGraph: (entityName: string, depth = 2) =>
      request<KnowledgeEntityGraph>(
        `/api/v1/knowledge/entities/${encodeURIComponent(entityName)}?depth=${depth}`,
      ),
    stats: () => request<KnowledgeStats>('/api/v1/knowledge/stats'),
    documentTriples: (docId: string) =>
      request<{ doc_id: string; triples: Record<string, unknown>[]; total: number }>(
        `/api/v1/knowledge/documents/${docId}/triples`,
      ),
    confidenceSummary: () =>
      request<ConfidenceSummary>('/api/v1/knowledge/provenance/confidence-summary'),
    entityProvenance: (entityName: string, minConfidence = 0) =>
      request<{ entity: string; sources: ProvenanceSource[]; total: number }>(
        `/api/v1/knowledge/provenance/entity/${encodeURIComponent(entityName)}?min_confidence=${minConfidence}`,
      ),
    disputeTriple: (tripleId: string) =>
      request<{ success: boolean; triple_id: string }>(
        `/api/v1/knowledge/triples/${tripleId}/dispute`,
        { method: 'PATCH' },
      ),
    riskAnalysis: (body: { text?: string; doc_ids?: string[] } = {}) =>
      request<RiskAnalysisResponse>('/api/v1/knowledge/risk-analysis', {
        method: 'POST',
        body: JSON.stringify({ text: body.text ?? '', doc_ids: body.doc_ids }),
      }),
  },

  reasoning: {
    analyzeDocument: (docId: string) =>
      request<DocumentAnalysisResponse>(`/api/v1/reasoning/analyze/${docId}`, {
        method: 'POST',
      }),
    compareDocuments: (docIds: string[]) =>
      request<CompareDocumentsResponse>('/api/v1/reasoning/compare', {
        method: 'POST',
        body: JSON.stringify({ doc_ids: docIds }),
      }),
  },

  profiles: {
    list: () => request<UserProfile[]>('/api/v1/profiles'),
    active: () => request<UserProfile | null>('/api/v1/profiles/active'),
    create: (data: Omit<UserProfile, 'id' | 'is_active' | 'created_at'>) =>
      request<UserProfile>('/api/v1/profiles', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<UserProfile>) =>
      request<UserProfile>(`/api/v1/profiles/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    activate: (id: string) =>
      request<UserProfile>(`/api/v1/profiles/${id}/activate`, { method: 'POST' }),
    delete: (id: string) =>
      request<null>(`/api/v1/profiles/${id}`, { method: 'DELETE' }),
  },
}
