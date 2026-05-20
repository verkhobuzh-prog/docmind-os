import { create } from "zustand";

interface DocumentsState {
  selectedIds: string[];
  toggleSelect: (id: string) => void;
  clearSelection: () => void;
}

export const useDocumentsStore = create<DocumentsState>((set) => ({
  selectedIds: [],
  toggleSelect: (id) =>
    set((s) => ({
      selectedIds: s.selectedIds.includes(id)
        ? s.selectedIds.filter((x) => x !== id)
        : [...s.selectedIds, id],
    })),
  clearSelection: () => set({ selectedIds: [] }),
}));
