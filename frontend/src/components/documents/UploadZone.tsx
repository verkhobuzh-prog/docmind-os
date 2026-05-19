import { useCallback, useState } from "react";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onUpload: (file: File) => void;
  loading?: boolean;
}

export function UploadZone({ onUpload, loading }: UploadZoneProps) {
  const [drag, setDrag] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors",
        drag ? "border-accent bg-accent/10" : "border-slate-600 hover:border-slate-500",
        loading && "pointer-events-none opacity-50"
      )}
    >
      <Upload className="mb-3 h-10 w-10 text-slate-400" />
      <p className="text-sm font-medium text-slate-200">Drop file or click to upload</p>
      <p className="mt-1 text-xs text-slate-500">PDF, TXT, Markdown, Excel (max 50MB)</p>
      <input
        type="file"
        className="hidden"
        accept=".pdf,.txt,.md,.xlsx,.xls"
        disabled={loading}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload(file);
        }}
      />
    </label>
  );
}
