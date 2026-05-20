export type DocumentStatus = "uploaded" | "parsing" | "indexed" | "failed";

export interface Document {
  id: string;
  org_id?: string | null;
  user_id: string;
  filename: string;
  title: string;
  storage_path: string;
  mime_type?: string | null;
  size_bytes: number;
  status: DocumentStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
}

export interface DocumentUploadResponse {
  document: Document;
  signed_url?: string | null;
  message: string;
}

export interface Citation {
  document_id: string;
  chunk_index: number;
  snippet: string;
  label?: string | null;
}

export interface Source {
  document_id: string;
  chunk_index: number;
  chunk_id?: string | null;
  snippet: string;
  score: number;
  filename?: string | null;
  vector_score?: number | null;
  fts_score?: number | null;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  citations: Citation[];
  model: string;
  query: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  sources?: Source[];
  model?: string;
  timestamp: Date;
}

export type TrustLevel = "standard" | "strict" | "maximum";

export interface UserProfile {
  id: string;
  email?: string | null;
  role?: string | null;
}
