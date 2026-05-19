import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Network, Search, Loader2, AlertCircle } from 'lucide-react'

export function KnowledgePage() {
  const [entityName, setEntityName] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  const { data: stats } = useQuery({
    queryKey: ['knowledge', 'stats'],
    queryFn: api.knowledge.stats,
  })

  const {
    data: graph,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['knowledge', 'entity', searchTerm],
    queryFn: () => api.knowledge.entityGraph(searchTerm),
    enabled: Boolean(searchTerm),
    retry: false,
  })

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    setSearchTerm(entityName.trim())
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Network className="w-6 h-6 text-brand-600" />
          Knowledge Graph
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Semantic knowledge graph from your documents
        </p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <StatCard label="Triples in DB" value={stats.total_triples_in_db} />
          <StatCard label="Graph DB" value={stats.graph_enabled ? 'On' : 'Off'} />
          <StatCard label="Extraction" value={stats.triple_extraction_enabled ? 'On' : 'Off'} />
        </div>
      )}

      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={entityName}
            onChange={(e) => setEntityName(e.target.value)}
            placeholder="Entity name (e.g. Acme Corp)"
            className="input pl-10 w-full"
          />
        </div>
        <button type="submit" className="btn-primary px-4" disabled={!entityName.trim()}>
          Search
        </button>
      </form>

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading graph...
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 text-red-600 bg-red-50 dark:bg-red-900/20 rounded-lg p-4 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          {error instanceof Error ? error.message : 'Failed to load graph'}
        </div>
      )}

      {graph && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium text-gray-900 dark:text-white">{graph.entity}</span>
            {' · depth '}{graph.depth}{' · '}{graph.total_nodes} nodes · {graph.total_edges} edges
          </p>
          {graph.nodes.length === 0 ? (
            <p className="text-sm text-gray-500">No relationships found.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="card p-4">
                <h2 className="text-sm font-semibold mb-3">Nodes</h2>
                <ul className="space-y-2 text-sm max-h-64 overflow-auto">
                  {graph.nodes.map((node) => (
                    <li key={node.id} className="flex justify-between gap-2">
                      <span className="font-medium truncate">{node.name}</span>
                      <span className="text-gray-400 text-xs flex-shrink-0">{node.type}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="card p-4">
                <h2 className="text-sm font-semibold mb-3">Edges</h2>
                <ul className="space-y-2 text-sm max-h-64 overflow-auto">
                  {graph.edges.map((edge, i) => (
                    <li key={`${edge.source}-${edge.target}-${i}`} className="text-gray-600 dark:text-gray-400">
                      <span className="text-gray-900 dark:text-white">{edge.type}</span>
                      {edge.confidence != null ? ` · ${Math.round(edge.confidence * 100)}%` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-lg font-semibold text-gray-900 dark:text-white mt-1">{value}</p>
    </div>
  )
}
