import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export interface IngestionProgressUpdate {
  doc_id: string
  status: string
  progress: number
  label: string
  event?: string | null
  is_terminal: boolean
  is_failed: boolean
}

export interface UseIngestionProgressOptions {
  /** Connect only when true (default: true). */
  enabled?: boolean
}

function toWsBase(httpBase: string): string {
  if (httpBase.startsWith('https://')) {
    return `wss://${httpBase.slice('https://'.length)}`
  }
  if (httpBase.startsWith('http://')) {
    return `ws://${httpBase.slice('http://'.length)}`
  }
  return httpBase
}

export function buildIngestionWsUrl(docId: string, token?: string | null): string {
  const wsBase = toWsBase(API_BASE)
  const path = `/api/v1/documents/${docId}/ingestion/ws`
  if (!token) {
    return `${wsBase}${path}`
  }
  return `${wsBase}${path}?token=${encodeURIComponent(token)}`
}

export function useIngestionProgress(
  docId: string | null | undefined,
  options: UseIngestionProgressOptions = {},
) {
  const { enabled = true } = options
  const token = useAuthStore((state) => state.token)

  const [update, setUpdate] = useState<IngestionProgressUpdate | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!enabled || !docId) {
      setUpdate(null)
      setIsConnected(false)
      setError(null)
      return
    }

    setUpdate(null)
    setError(null)

    const url = buildIngestionWsUrl(docId, token)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(String(event.data)) as IngestionProgressUpdate
        setUpdate(payload)
        if (payload.is_terminal) {
          ws.close()
        }
      } catch {
        setError('Invalid ingestion progress payload')
      }
    }

    ws.onerror = () => {
      setError('WebSocket connection failed')
    }

    ws.onclose = () => {
      setIsConnected(false)
      if (wsRef.current === ws) {
        wsRef.current = null
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
      setIsConnected(false)
    }
  }, [docId, token, enabled])

  return {
    progress: update?.progress ?? 0,
    status: update?.status ?? null,
    label: update?.label ?? (isConnected ? 'Processing…' : 'Connecting…'),
    isTerminal: update?.is_terminal ?? false,
    isFailed: update?.is_failed ?? false,
    isConnected,
    error,
    update,
  }
}
