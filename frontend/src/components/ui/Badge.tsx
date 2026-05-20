import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  uploaded: "bg-slate-600 text-slate-200",
  parsing: "bg-amber-600/30 text-amber-300 border border-amber-500/50",
  indexed: "bg-emerald-600/30 text-emerald-300 border border-emerald-500/50",
  failed: "bg-red-600/30 text-red-300 border border-red-500/50",
  default: "bg-surface-overlay text-slate-300",
};

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: React.ReactNode;
  variant?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variants[variant] || variants.default,
        className
      )}
    >
      {children}
    </span>
  );
}
