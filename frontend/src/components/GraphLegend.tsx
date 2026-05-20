import {
  EDGE_CONFIDENCE_HIGH,
  EDGE_CONFIDENCE_LOW,
  EDGE_CONFIDENCE_MEDIUM,
  NODE_COLORS,
} from '@/components/graphColors'

const ENTITY_TYPES = [
  'PERSON',
  'ORGANIZATION',
  'AGREEMENT',
  'ASSET',
  'EVENT',
  'POLICY',
  'LEGAL_CASE',
  'FINANCIAL_RECORD',
  'LOCATION',
  'PROJECT',
] as const

const CONFIDENCE_LEVELS = [
  { label: 'High', range: '≥ 0.8', color: EDGE_CONFIDENCE_HIGH },
  { label: 'Medium', range: '0.5–0.8', color: EDGE_CONFIDENCE_MEDIUM },
  { label: 'Low', range: '< 0.5', color: EDGE_CONFIDENCE_LOW },
] as const

function formatEntityType(type: string): string {
  return type
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
}

export default function GraphLegend() {
  return (
    <details className="group rounded-lg bg-gray-800 text-sm text-gray-200">
      <summary className="cursor-pointer select-none px-4 py-2.5 font-medium text-gray-100 hover:text-white list-none flex items-center gap-2 [&::-webkit-details-marker]:hidden">
        <span className="text-gray-400 group-open:rotate-90 transition-transform inline-block">▶</span>
        Legend
      </summary>

      <div className="px-4 pb-4 pt-1 grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-gray-700">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
            Entity Types
          </h4>
          <ul className="space-y-1.5">
            {ENTITY_TYPES.map((type) => (
              <li key={type} className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: NODE_COLORS[type] }}
                  aria-hidden
                />
                <span>{formatEntityType(type)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
            Edge Confidence
          </h4>
          <ul className="space-y-1.5">
            {CONFIDENCE_LEVELS.map(({ label, range, color }) => (
              <li key={label} className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: color }}
                  aria-hidden
                />
                <span>
                  {label} ({range})
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-gray-400 italic">
            Edge width reflects confidence level
          </p>
        </div>
      </div>
    </details>
  )
}
