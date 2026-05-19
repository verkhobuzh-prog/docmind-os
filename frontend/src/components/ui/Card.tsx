import { cn } from "@/lib/utils";

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-700/50 bg-surface-raised p-6 shadow-lg",
        className
      )}
    >
      {children}
    </div>
  );
}
