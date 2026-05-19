export const NODE_COLORS: Record<string, string> = {
  PERSON: '#3B82F6',
  ORGANIZATION: '#8B5CF6',
  AGREEMENT: '#10B981',
  ASSET: '#F59E0B',
  EVENT: '#F97316',
  POLICY: '#EF4444',
  LEGAL_CASE: '#EC4899',
  FINANCIAL_RECORD: '#14B8A6',
  LOCATION: '#84CC16',
  PROJECT: '#6366F1',
  DEFAULT: '#6B7280',
}

export const EDGE_CONFIDENCE_HIGH = '#10B981'
export const EDGE_CONFIDENCE_MEDIUM = '#F59E0B'
export const EDGE_CONFIDENCE_LOW = '#EF4444'

export function edgeColor(confidence: number): string {
  if (confidence >= 0.8) return EDGE_CONFIDENCE_HIGH
  if (confidence >= 0.5) return EDGE_CONFIDENCE_MEDIUM
  return EDGE_CONFIDENCE_LOW
}
