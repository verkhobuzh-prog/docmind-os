import cytoscape from 'cytoscape'
import { useEffect, useRef } from 'react'
import { NODE_COLORS, edgeColor } from '@/components/graphColors'

export interface GraphNode {
  id: string
  name: string
  type: string
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  confidence: number
}

export interface KnowledgeGraphProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick?: (node: GraphNode) => void
  height?: string
}

function layoutConfig(nodeCount: number): cytoscape.LayoutOptions {
  return {
    name: nodeCount > 20 ? 'cose' : 'cose',
    animate: true,
    animationDuration: 500,
    randomize: false,
    nodeRepulsion: 8000,
    idealEdgeLength: 150,
    gravity: 0.8,
  }
}

export default function KnowledgeGraph({
  nodes,
  edges,
  onNodeClick,
  height = '500px',
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const onNodeClickRef = useRef(onNodeClick)
  onNodeClickRef.current = onNodeClick

  useEffect(() => {
    if (!containerRef.current) return

    if (nodes.length === 0) {
      cyRef.current?.destroy()
      cyRef.current = null
      return
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...nodes.map((n) => ({
          data: { ...n, id: n.id, label: n.name, type: n.type },
        })),
        ...edges.map((e, i) => ({
          data: {
            id: `e-${i}`,
            source: e.source,
            target: e.target,
            label: e.type.replace('_', ' '),
            confidence: e.confidence,
          },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: cytoscape.NodeSingular) => {
              const type = String(ele.data('type') ?? '').toUpperCase()
              return NODE_COLORS[type] ?? NODE_COLORS.DEFAULT
            },
            label: 'data(label)',
            color: '#fff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '11px',
            width: '120px',
            height: '40px',
            shape: 'roundrectangle',
            'text-wrap': 'wrap',
            'text-max-width': '110px',
            'border-width': 2,
            'border-color': '#fff',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#60A5FA',
          },
        },
        {
          selector: 'edge',
          style: {
            width: (ele: cytoscape.EdgeSingular) =>
              Math.max(1, (ele.data('confidence') as number) * 4),
            'line-color': (ele: cytoscape.EdgeSingular) =>
              edgeColor(ele.data('confidence') as number),
            'target-arrow-color': (ele: cytoscape.EdgeSingular) =>
              edgeColor(ele.data('confidence') as number),
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9px',
            color: '#9CA3AF',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
      ],
      layout: layoutConfig(nodes.length),
    })

    cyRef.current = cy

    cy.on('tap', 'node', (evt) => {
      const node = evt.target
      onNodeClickRef.current?.({
        id: node.data('id'),
        name: node.data('label'),
        type: node.data('type'),
      })
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [nodes, edges])

  const handleFit = () => cyRef.current?.fit(undefined, 50)
  const handleCenter = () => cyRef.current?.center()
  const handleReset = () => {
    const cy = cyRef.current
    if (!cy) return
    cy.layout(layoutConfig(nodes.length)).run()
    cy.fit(undefined, 50)
    cy.center()
  }

  if (nodes.length === 0) {
    return (
      <div
        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-surface-dark-2 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400"
        style={{ height }}
      >
        No graph data. Search for an entity above.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={handleFit} className="btn-ghost text-xs px-3 py-1.5">
          Fit
        </button>
        <button type="button" onClick={handleCenter} className="btn-ghost text-xs px-3 py-1.5">
          Center
        </button>
        <button type="button" onClick={handleReset} className="btn-ghost text-xs px-3 py-1.5">
          Reset
        </button>
        <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
          {nodes.length} nodes · {edges.length} edges
        </span>
      </div>
      <div
        ref={containerRef}
        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark-1 overflow-hidden"
        style={{ height }}
      />
    </div>
  )
}
