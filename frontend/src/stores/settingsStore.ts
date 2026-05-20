import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { TrustLevel } from "@/types";

interface SettingsState {
  trustLevel: TrustLevel;
  requireCitations: boolean;
  blockSensitiveUploads: boolean;
  setTrustLevel: (level: TrustLevel) => void;
  setRequireCitations: (value: boolean) => void;
  setBlockSensitiveUploads: (value: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      trustLevel: "strict",
      requireCitations: true,
      blockSensitiveUploads: false,

      setTrustLevel: (trustLevel) =>
        set({
          trustLevel,
          requireCitations: trustLevel !== "standard",
          blockSensitiveUploads: trustLevel === "maximum",
        }),

      setRequireCitations: (requireCitations) => set({ requireCitations }),

      setBlockSensitiveUploads: (blockSensitiveUploads) => set({ blockSensitiveUploads }),
    }),
    { name: "docmind-settings" }
  )
);

export const TRUST_LEVEL_INFO: Record<
  TrustLevel,
  { label: string; description: string; color: string }
> = {
  standard: {
    label: "Standard",
    description: "Balanced mode for trusted internal teams.",
    color: "text-trust-standard",
  },
  strict: {
    label: "Strict",
    description: "Blocks prompt injection patterns; requires citations in answers.",
    color: "text-trust-strict",
  },
  maximum: {
    label: "Maximum",
    description: "Highest guardrails — blocks risky queries and sensitive uploads.",
    color: "text-trust-maximum",
  },
};
