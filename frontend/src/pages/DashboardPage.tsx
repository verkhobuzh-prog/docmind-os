import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Document } from "@/lib/api";
import { useDocumentsStore } from "@/stores/documentsStore";
import { UploadZone } from "@/components/documents/UploadZone";
import { DocumentCard } from "@/components/documents/DocumentCard";
import { Button } from "@/components/ui/Button";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const { selectedIds, toggleSelect } = useDocumentsStore();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const data = await api.documents.list()
      if (Array.isArray(data)) return { items: data, total: data.length }
      const list = data as { items: Document[]; total: number }
      return { items: list.items, total: list.total }
    },
    refetchInterval: 5000,
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const res = await api.documents.upload(file)
      const wrapped = res as Document & { document?: Document }
      return wrapped.document ?? wrapped
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const ingestMutation = useMutation({
    mutationFn: (id: string) => api.documents.ingest(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Documents</h1>
          <p className="mt-1 text-slate-400">Upload and manage your document library</p>
        </div>
        <Button variant="secondary" onClick={() => refetch()}>
          Refresh
        </Button>
      </div>

      <UploadZone onUpload={(f) => uploadMutation.mutate(f)} loading={uploadMutation.isPending} />

      {uploadMutation.isError && (
        <p className="mt-4 text-sm text-red-400">{(uploadMutation.error as Error).message}</p>
      )}

      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-slate-200">
          Your documents ({data?.total ?? 0})
        </h2>
        {isLoading && <p className="text-slate-400">Loading...</p>}
        {error && <p className="text-red-400">{(error as Error).message}</p>}
        <div className="space-y-3">
          {data?.items.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              selected={selectedIds.includes(doc.id)}
              onSelect={toggleSelect}
              onIngest={(id) => ingestMutation.mutate(id)}
            />
          ))}
          {!isLoading && data?.items.length === 0 && (
            <p className="text-center text-slate-500 py-12">No documents yet. Upload your first file.</p>
          )}
        </div>
      </div>
    </div>
  );
}
