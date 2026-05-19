import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type ChatMessage } from '@/lib/api'
import { Send, Bot, User, FileText, Loader2, AlertCircle, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function normalizeSources(
  sources: ChatMessage['sources'] | Array<Record<string, unknown>> | undefined
): ChatMessage['sources'] {
  if (!sources?.length) return undefined
  return sources.map((s) => {
    const src = s as {
      chunk_id?: string
      snippet?: string
      content?: string
      score?: number
      similarity?: number
    }
    return {
      chunk_id: String(src.chunk_id ?? ''),
      content: src.content ?? src.snippet ?? '',
      similarity: src.similarity ?? src.score ?? 0,
    }
  })
}

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { data: docs = [] } = useQuery({ queryKey: ['documents'], queryFn: api.documents.list })
  const indexedDocs = docs.filter(d => d.status === 'indexed')

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return
    const query = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setIsLoading(true)

    try {
      const res = await api.chat.query(query)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        sources: normalizeSources(res.sources as Array<Record<string, unknown>>),
        citations: res.citations,
        risk_score: res.risk_score,
        risk_level: res.risk_level,
        risk_warning: res.risk_warning,
      }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Помилка'
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ Помилка: ${msg}` }])
    } finally {
      setIsLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-2 dark:border-surface-dark-3 bg-white dark:bg-surface-dark-1">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-500" />
            Chat AI
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {indexedDocs.length > 0
              ? `${indexedDocs.length} документ${indexedDocs.length === 1 ? '' : 'ів'} в базі знань`
              : 'Спочатку завантажте документи'}
          </p>
        </div>
      </div>

      {/* No docs warning */}
      {indexedDocs.length === 0 && (
        <div className="mx-6 mt-4">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
            <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <p className="text-sm text-amber-700 dark:text-amber-400">
              Немає проіндексованих документів. Перейдіть до <strong>Документи</strong> та завантажте файли.
            </p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center pb-8">
            <div className="w-16 h-16 rounded-2xl bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center">
              <Bot className="w-8 h-8 text-brand-500" />
            </div>
            <div>
              <p className="font-medium text-gray-900 dark:text-white mb-1">Запитайте про ваші документи</p>
              <p className="text-sm text-gray-400">Отримуйте відповіді з точними цитатами з джерел</p>
            </div>
            {/* Quick prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 max-w-lg">
              {[
                'Що є головним у цих документах?',
                'Які ключові дати та терміни?',
                'Перелічи головні зобов\'язання сторін',
                'Які є ризики та застереження?',
              ].map(q => (
                <button
                  key={q}
                  onClick={() => { setInput(q); inputRef.current?.focus() }}
                  className="text-left text-xs p-3 rounded-lg border border-surface-2 dark:border-surface-dark-3
                             text-gray-600 dark:text-gray-400 hover:border-brand-300 hover:text-brand-600
                             dark:hover:text-brand-400 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 animate-fade-in ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
              ${msg.role === 'user'
                ? 'bg-brand-100 dark:bg-brand-900/30'
                : 'bg-gray-100 dark:bg-surface-dark-2'}
            `}>
              {msg.role === 'user'
                ? <User className="w-4 h-4 text-brand-600" />
                : <Bot className="w-4 h-4 text-gray-500" />}
            </div>
            <div className={`flex-1 max-w-2xl ${msg.role === 'user' ? 'flex flex-col items-end' : ''}`}>
              <div className={`
                px-4 py-3 rounded-2xl text-sm leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-sm'
                  : 'bg-white dark:bg-surface-dark-1 border border-surface-2 dark:border-surface-dark-3 text-gray-900 dark:text-gray-100 rounded-tl-sm'}
              `}>
                {msg.role === 'assistant' && (msg.risk_score ?? 0) > 50 && (
                  <div className="mb-3 flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-xs">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>
                      ⚠️ This answer contains low-confidence information. Risk:{' '}
                      <strong>{msg.risk_level ?? 'unknown'}</strong>
                      {msg.risk_warning ? ` — ${msg.risk_warning}` : ''}
                    </span>
                  </div>
                )}
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  msg.content
                )}
              </div>

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-gray-400 font-medium">Джерела:</p>
                  {msg.sources.slice(0, 3).map((src, si) => (
                    <div key={si} className="flex items-start gap-2 p-2 rounded-lg bg-surface-0 dark:bg-surface-dark-2 border border-surface-2 dark:border-surface-dark-3">
                      <FileText className="w-3 h-3 text-brand-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{src.content}</p>
                      <span className="text-xs text-gray-300 dark:text-gray-600 flex-shrink-0">
                        {Math.round(src.similarity * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-surface-dark-2 flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-500" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white dark:bg-surface-dark-1 border border-surface-2 dark:border-surface-dark-3">
              <div className="flex gap-1 items-center h-4">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-dot" style={{animationDelay:'0ms'}} />
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-dot" style={{animationDelay:'200ms'}} />
                <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-dot" style={{animationDelay:'400ms'}} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-surface-2 dark:border-surface-dark-3 bg-white dark:bg-surface-dark-1">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Задайте питання про документи... (Enter — відправити, Shift+Enter — новий рядок)"
              className="input resize-none min-h-[44px] max-h-32 py-2.5 pr-4 leading-relaxed"
              rows={1}
              disabled={isLoading || indexedDocs.length === 0}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading || indexedDocs.length === 0}
            className="btn-primary py-2.5 px-4 flex-shrink-0"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}
