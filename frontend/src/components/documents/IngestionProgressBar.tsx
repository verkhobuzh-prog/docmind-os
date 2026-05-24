import { AlertCircle, Loader2 } from 'lucide-react'
import { useIngestionProgress } from '@/hooks/useIngestionProgress'
import { cn } from '@/lib/utils'

interface IngestionProgressBarProps {
  docId: string
  className?: string
}

export function IngestionProgressBar({ docId, className }: IngestionProgressBarProps) {
  const { progress, label, isFailed, isConnected, error } = useIngestionProgress(docId)

  const clampedProgress = Math.min(100, Math.max(0, progress))
  const displayLabel = error ?? label

  return (
    <div
      className={cn('mt-2 w-full max-w-sm', className)}
      role="status"
      aria-live="polite"
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          {!isConnected && !error && (
            <Loader2 className="h-3 w-3 flex-shrink-0 animate-spin text-gray-400" aria-hidden />
          )}
          {isFailed && (
            <AlertCircle className="h-3 w-3 flex-shrink-0 text-red-500" aria-hidden />
          )}
          <span
            className={cn(
              'truncate text-xs',
              isFailed || error
                ? 'text-red-600 dark:text-red-400'
                : 'text-gray-500 dark:text-gray-400',
            )}
          >
            {displayLabel}
          </span>
        </div>
        <span className="flex-shrink-0 text-xs tabular-nums text-gray-400">
          {clampedProgress}%
        </span>
      </div>

      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2 dark:bg-surface-dark-3"
        role="progressbar"
        aria-valuenow={clampedProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={displayLabel}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            isFailed
              ? 'bg-red-500'
              : clampedProgress >= 100
                ? 'bg-green-500'
                : 'bg-brand-500',
          )}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  )
}
