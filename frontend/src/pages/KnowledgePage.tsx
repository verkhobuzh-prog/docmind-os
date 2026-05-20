import { useState, useEffect, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  api,
  type Document,
  type DocumentAnalysisResponse,
  type KnowledgeEntityGraph,
  type ProvenanceSource,
  type ReasoningFinding,
  type RiskAnalysisResponse,
} from '@/lib/api'
import KnowledgeGraph, { type GraphNode } from '@/components/KnowledgeGraph'
import GraphLegend from '@/components/GraphLegend'
import { Network, Search, Loader2, AlertCircle, BarChart3, Flag, FileSearch } from 'lucide-react'

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

  useEffect(() => {
    const trimmed = entityName.trim()
    if (!trimmed) {
      setSearchTerm('')
      return
    }
    const timer = window.setTimeout(() => setSearchTerm(trimmed), 500)
    return () => window.clearTimeout(timer)
  }, [entityName])

  const handleNodeClick = (node: GraphNode) => {
    setEntityName(node.name)
    setSearchTerm(node.name)
    toast.success(`Selected: ${node.name} (${node.type})`)
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

      {searchTerm && graph && graph.nodes.length > 0 && (
        <EntityGraph graph={graph} onNodeClick={handleNodeClick} />
      )}

      {searchTerm && graph && graph.nodes.length === 0 && !isLoading && (
        <p className="text-sm text-gray-500">No relationships found for &ldquo;{graph.entity}&rdquo;.</p>
      )}

      <section className="space-y-4 pt-2 border-t border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-brand-600" />
          Provenance Analytics
        </h2>
        <ProvenanceStats />
        {searchTerm && <EntityProvenance entityName={searchTerm} />}
      </section>

      <section className="space-y-4 pt-2 border-t border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <FileSearch className="w-5 h-5 text-brand-600" />
          Document Analysis
        </h2>
        <DocumentAnalysis />
      </section>
    </div>
  )
}

function EntityGraph({
  graph,
  onNodeClick,
}: {
  graph: KnowledgeEntityGraph
  onNodeClick: (node: GraphNode) => void
}) {
  const nodes: GraphNode[] = graph.nodes.map((n) => ({
    id: n.id,
    name: n.name,
    type: n.type,
  }))
  const edges = graph.edges.map((e) => ({
    source: e.source,
    target: e.target,
    type: e.type,
    confidence: e.confidence ?? 0,
  }))

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        <span className="font-medium text-gray-900 dark:text-white">{graph.entity}</span>
        {' ? depth '}
        {graph.depth}
        {' ? '}
        {graph.total_nodes} nodes ? {graph.total_edges} edges
      </p>

      <KnowledgeGraph
        nodes={nodes}
        edges={edges}
        onNodeClick={onNodeClick}
        height="550px"
      />
      <GraphLegend />

      <details className="rounded-lg border border-gray-200 dark:border-gray-700">
        <summary className="cursor-pointer select-none px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white list-none">
          Show raw data
        </summary>
        <div className="grid gap-4 md:grid-cols-2 p-4 pt-0 border-t border-gray-200 dark:border-gray-700">
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-3">Nodes</h3>
            <ul className="space-y-2 max-h-64 overflow-auto font-mono text-xs">
              {graph.nodes.map((node) => (
                <li key={node.id} className="flex justify-between gap-2">
                  <span className="truncate">{node.name}</span>
                  <span className="text-gray-400 flex-shrink-0">{node.type}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-3">Edges</h3>
            <ul className="space-y-2 max-h-64 overflow-auto font-mono text-xs">
              {graph.edges.map((edge, i) => (
                <li key={`${edge.source}-${edge.target}-${i}`} className="text-gray-600 dark:text-gray-400">
                  <span className="text-gray-900 dark:text-white">{edge.type}</span>
                  {' '}
                  {edge.source} ? {edge.target}
                  {edge.confidence != null ? ` ? ${Math.round(edge.confidence * 100)}%` : ''}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </details>
    </div>
  )
}

function ProvenanceStats() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['knowledge', 'confidence-summary'],
    queryFn: api.knowledge.confidenceSummary,
  })

  const {
    data: riskData,
    isLoading: riskLoading,
    isError: riskError,
  } = useQuery({
    queryKey: ['knowledge', 'risk-analysis'],
    queryFn: () => api.knowledge.riskAnalysis({}),
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading provenance stats...
      </div>
    )
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-red-600 dark:text-red-400">Failed to load confidence summary.</p>
    )
  }

  const avgPct = Math.round(data.avg_confidence * 100)

  return (
    <div className="space-y-4">
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <div className="card p-4">
        <p className="text-xs text-gray-500 dark:text-gray-400">Total Triples</p>
        <p className="text-2xl font-semibold text-gray-900 dark:text-white mt-1">
          {data.total_triples}
        </p>
      </div>

      <div className="card p-4">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Avg Confidence</p>
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="font-semibold text-gray-900 dark:text-white">{avgPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${avgPct}%` }}
          />
        </div>
      </div>

      <div className="card p-4 flex flex-col justify-center gap-2">
        <p className="text-xs text-gray-500 dark:text-gray-400">Confidence bands</p>
        <div className="flex flex-wrap gap-2">
          <ConfidenceBadge label="High" count={data.high_confidence} color="green" />
          <ConfidenceBadge label="Medium" count={data.medium_confidence} color="yellow" />
          <ConfidenceBadge label="Low" count={data.low_confidence} color="red" />
        </div>
      </div>

      <div className="card p-4">
        <p className="text-xs text-gray-500 dark:text-gray-400">Disputed</p>
        <p
          className={`text-2xl font-semibold mt-1 ${
            data.disputed > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'
          }`}
        >
          {data.disputed}
        </p>
        {data.disputed > 0 && (
          <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
            <Flag className="w-3 h-3" />
            Requires review
          </p>
        )}
      </div>
    </div>

      <RiskAssessment data={riskData} isLoading={riskLoading} isError={riskError} />
    </div>
  )
}

type RiskLevel = RiskAnalysisResponse['risk_level']

function RiskBadge({ level }: { level: RiskLevel }) {
  const config: Record<string, { label: string; className: string }> = {
    low: {
      label: '? LOW RISK',
      className: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    },
    medium: {
      label: '? MEDIUM RISK',
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    },
    high: {
      label: '? HIGH RISK',
      className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    },
    critical: {
      label: '? CRITICAL RISK',
      className: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
    },
  }
  const normalized = String(level).toLowerCase()
  const item = config[normalized] ?? config.low
  return (
    <span className={`inline-block px-4 py-2 rounded-lg text-sm font-bold tracking-wide ${item.className}`}>
      {item.label}
    </span>
  )
}

function RiskAssessment({
  data,
  isLoading,
  isError,
}: {
  data: RiskAnalysisResponse | undefined
  isLoading: boolean
  isError: boolean
}) {
  return (
    <div className="card p-5 space-y-4">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Risk Assessment</h3>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Analyzing knowledge risk...
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load risk analysis.</p>
      )}

      {!isLoading && !isError && data && (
        <>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Risk Score</p>
              <p className="text-4xl font-bold text-gray-900 dark:text-white">{data.risk_score}</p>
              <p className="text-xs text-gray-400 mt-0.5">0?100</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Risk Level</p>
              <RiskBadge level={data.risk_level} />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Low Confidence Facts</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white mt-1">
                {data.low_confidence_triples}
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Disputed Facts</p>
              <p className="text-xl font-semibold text-gray-900 dark:text-white mt-1">
                {data.disputed_triples}
              </p>
            </div>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            {data.analyzed_documents} document(s) ? {data.total_triples} triple(s) analyzed
          </p>

          {data.risk_score > 50 && data.explanation && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{data.explanation}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ConfidenceBadge({
  label,
  count,
  color,
}: {
  label: string
  count: number
  color: 'green' | 'yellow' | 'red'
}) {
  const styles = {
    green: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    red: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${styles[color]}`}>
      {label}
      <span className="font-semibold">{count}</span>
    </span>
  )
}

function EntityProvenance({ entityName }: { entityName: string }) {
  const qc = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['knowledge', 'provenance', entityName],
    queryFn: () => api.knowledge.entityProvenance(entityName),
    enabled: Boolean(entityName),
  })

  const disputeMutation = useMutation({
    mutationFn: (tripleId: string) => api.knowledge.disputeTriple(tripleId),
    onSuccess: () => {
      toast.success('Marked as disputed')
      qc.invalidateQueries({ queryKey: ['knowledge', 'provenance', entityName] })
      qc.invalidateQueries({ queryKey: ['knowledge', 'confidence-summary'] })
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to mark as disputed')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading evidence sources...
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600 dark:text-red-400">Failed to load evidence sources.</p>
    )
  }

  const sources = data?.sources ?? []

  return (
    <div className="card p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
        Evidence Sources ? {entityName}
        <span className="ml-2 text-gray-400 font-normal">({sources.length})</span>
      </h3>

      {sources.length === 0 ? (
        <p className="text-sm text-gray-500">No provenance records for this entity.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
                <th className="py-2 pr-3 font-medium">Document</th>
                <th className="py-2 pr-3 font-medium">Quote</th>
                <th className="py-2 pr-3 font-medium w-24">Confidence</th>
                <th className="py-2 pr-3 font-medium w-28">Status</th>
                <th className="py-2 font-medium w-24">Action</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <ProvenanceRow
                  key={source.id}
                  source={source}
                  disputing={disputeMutation.isPending && disputeMutation.variables === source.id}
                  onDispute={() => disputeMutation.mutate(source.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ProvenanceRow({
  source,
  disputing,
  onDispute,
}: {
  source: ProvenanceSource
  disputing: boolean
  onDispute: () => void
}) {
  const pct = Math.round(source.confidence * 100)
  const isDisputed = source.validation_status === 'disputed'

  return (
    <tr className="border-b border-gray-100 dark:border-gray-800 last:border-0">
      <td className="py-3 pr-3 align-top">
        <code className="text-xs text-gray-600 dark:text-gray-400 break-all">
          {source.doc_id.slice(0, 8)}?
        </code>
      </td>
      <td className="py-3 pr-3 align-top text-gray-700 dark:text-gray-300 max-w-md">
        <p className="line-clamp-3">{source.evidence_quote || '?'}</p>
      </td>
      <td className="py-3 pr-3 align-top">
        <span className="font-medium text-gray-900 dark:text-white">{pct}%</span>
      </td>
      <td className="py-3 pr-3 align-top">
        <ValidationBadge status={source.validation_status} />
      </td>
      <td className="py-3 align-top">
        <button
          type="button"
          onClick={onDispute}
          disabled={isDisputed || disputing}
          className="text-xs px-2.5 py-1 rounded-md border border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {disputing ? '?' : isDisputed ? 'Disputed' : 'Dispute'}
        </button>
      </td>
    </tr>
  )
}

function ValidationBadge({ status }: { status: string }) {
  if (status === 'disputed') {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300">
        disputed
      </span>
    )
  }
  if (status === 'human-verified') {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300">
        verified
      </span>
    )
  }
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
      {status}
    </span>
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

function DocumentAnalysis() {
  const [selectedDocId, setSelectedDocId] = useState('')
  const [analysis, setAnalysis] = useState<DocumentAnalysisResponse | null>(null)

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: api.documents.list,
  })

  const analyzeMutation = useMutation({
    mutationFn: (docId: string) => api.reasoning.analyzeDocument(docId),
    onSuccess: (data) => {
      setAnalysis(data)
      if (data.total_findings === 0) {
        toast.success('Analysis complete ? no issues found')
      } else {
        toast.success(`Found ${data.total_findings} issue(s)`)
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Analysis failed')
    },
  })

  const indexedDocs = documents.filter((d) => d.status === 'indexed')

  return (
    <div className="card p-5 space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
        <DocumentSelector
          documents={indexedDocs}
          isLoading={docsLoading}
          value={selectedDocId}
          onChange={setSelectedDocId}
        />
        <AnalyzeButton
          disabled={!selectedDocId || analyzeMutation.isPending}
          isLoading={analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate(selectedDocId)}
        />
      </div>

      {analysis && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Risk score:{' '}
          <span className="font-semibold text-gray-800 dark:text-gray-200">{analysis.risk_score}</span>
          {' ? '}
          {analysis.total_findings} finding(s)
        </p>
      )}

      {analyzeMutation.isPending && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Running graph reasoning analysis...
        </div>
      )}

      {analysis && !analyzeMutation.isPending && <FindingsList findings={analysis.findings} />}
    </div>
  )
}

function DocumentSelector({
  documents,
  isLoading,
  value,
  onChange,
}: {
  documents: Document[]
  isLoading: boolean
  value: string
  onChange: (docId: string) => void
}) {
  return (
    <div className="flex-1 min-w-0">
      <label htmlFor="doc-analysis-select" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
        Document
      </label>
      <select
        id="doc-analysis-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={isLoading || documents.length === 0}
        className="input w-full"
      >
        <option value="">
          {isLoading
            ? 'Loading documents...'
            : documents.length === 0
              ? 'No indexed documents'
              : 'Select a document'}
        </option>
        {documents.map((doc) => (
          <option key={doc.id} value={doc.id}>
            {doc.filename} ({doc.id.slice(0, 8)}?)
          </option>
        ))}
      </select>
    </div>
  )
}

function AnalyzeButton({
  disabled,
  isLoading,
  onClick,
}: {
  disabled: boolean
  isLoading: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="btn-primary px-4 py-2.5 whitespace-nowrap flex items-center gap-2"
    >
      {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span aria-hidden>??</span>}
      Analyze Document
    </button>
  )
}

function FindingsList({ findings }: { findings: ReasoningFinding[] }) {
  if (findings.length === 0) {
    return <AnalysisEmptyState />
  }

  return (
    <div className="space-y-3">
      {findings.map((finding, index) => (
        <FindingCard key={`${finding.title}-${index}`} finding={finding} />
      ))}
    </div>
  )
}

function AnalysisEmptyState() {
  return (
    <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4 text-center text-sm text-green-700 dark:text-green-300">
      No issues found ? knowledge base looks clean ?
    </div>
  )
}

function FindingCard({ finding }: { finding: ReasoningFinding }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-1 p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={finding.severity} />
        <FindingTypeBadge type={finding.finding_type} />
        <span className="text-xs text-gray-400 ml-auto">
          {Math.round(finding.confidence * 100)}% conf.
        </span>
      </div>

      <h4 className="font-semibold text-gray-900 dark:text-white">{finding.title}</h4>
      <p className="text-sm text-gray-600 dark:text-gray-400">{finding.description}</p>

      {finding.entities_involved.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Entities</p>
          <div className="flex flex-wrap gap-1">
            {finding.entities_involved.map((entity) => (
              <span
                key={entity}
                className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
              >
                {entity}
              </span>
            ))}
          </div>
        </div>
      )}

      {finding.evidence.length > 0 && (
        <details className="group">
          <summary className="text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer list-none flex items-center gap-1">
            <span className="group-open:rotate-90 transition-transform inline-block">?</span>
            Evidence ({finding.evidence.length})
          </summary>
          <ul className="mt-2 space-y-1.5 pl-3 border-l-2 border-gray-200 dark:border-gray-700">
            {finding.evidence.map((quote, i) => (
              <li key={i} className="text-xs text-gray-600 dark:text-gray-400 italic">
                &ldquo;{quote}&rdquo;
              </li>
            ))}
          </ul>
        </details>
      )}

      {finding.recommendation && (
        <p className="text-sm text-green-700 dark:text-green-400 italic">{finding.recommendation}</p>
      )}
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  }
  const normalized = severity.toLowerCase()
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${styles[normalized] ?? styles.low}`}
    >
      {severity}
    </span>
  )
}

function FindingTypeBadge({ type }: { type: string }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
      {type.replace(/_/g, ' ')}
    </span>
  )
}
