import { FileText, RefreshCw } from "lucide-react";
import type { Document } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatBytes, formatDate } from "@/lib/utils";

const STATUS_LABELS: Record<string, string> = {
  uploaded: "Uploaded",
  parsing: "Processing",
  indexed: "Ready",
  failed: "Failed",
};

interface DocumentCardProps {
  doc: Document;
  onIngest?: (id: string) => void;
  onSelect?: (id: string) => void;
  selected?: boolean;
}

export function DocumentCard({ doc, onIngest, onSelect, selected }: DocumentCardProps) {
  return (
    <div
      className={`flex items-center gap-4 rounded-xl border p-4 transition-colors ${
        selected ? "border-accent bg-accent/10" : "border-slate-700/50 bg-surface-raised hover:border-slate-600"
      }`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-surface-overlay">
        <FileText className="h-6 w-6 text-accent" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-slate-100">{doc.filename}</p>
        <p className="text-xs text-slate-500">
          {formatBytes(doc.size_bytes)} · {formatDate(doc.created_at)}
        </p>
      </div>
      <Badge variant={doc.status}>{STATUS_LABELS[doc.status] || doc.status}</Badge>
      {doc.status !== "indexed" && doc.status !== "parsing" && onIngest && (
        <Button size="sm" variant="secondary" onClick={() => onIngest(doc.id)}>
          <RefreshCw className="h-4 w-4" />
          Index
        </Button>
      )}
      {onSelect && (
        <Button size="sm" variant={selected ? "primary" : "ghost"} onClick={() => onSelect(doc.id)}>
          {selected ? "Selected" : "Select"}
        </Button>
      )}
    </div>
  );
}
