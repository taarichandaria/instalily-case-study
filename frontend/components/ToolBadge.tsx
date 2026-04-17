"use client";

import { Check, Loader2, Search, Stethoscope, CheckCircle2, FileText, Wrench, MapPin, Globe, X } from "lucide-react";
import type { ToolActivity } from "@/lib/types";

const ICONS: Record<string, typeof Search> = {
  search_parts: Search,
  diagnose_symptom: Stethoscope,
  check_compatibility: CheckCircle2,
  get_part_details: FileText,
  get_install_guide: Wrench,
  find_model_number_location: MapPin,
  live_fetch_part: Globe,
};

const LABELS: Record<string, string> = {
  search_parts: "Searching parts",
  diagnose_symptom: "Diagnosing symptom",
  check_compatibility: "Checking compatibility",
  get_part_details: "Loading part details",
  get_install_guide: "Loading install guide",
  find_model_number_location: "Locating model sticker",
  live_fetch_part: "Fetching from PartSelect",
};

export function ToolBadge({ activity }: { activity: ToolActivity }) {
  const Icon = ICONS[activity.name] ?? Search;
  const label = LABELS[activity.name] ?? activity.name;
  const running = activity.status === "running";
  const error = activity.status === "error";

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border transition-colors ${
        error
          ? "border-red-200 bg-red-50 text-red-700"
          : running
            ? "border-[color:var(--ps-teal)]/30 bg-[color:var(--ps-teal-light)] text-[color:var(--ps-teal-dark)]"
            : "border-[color:var(--ps-teal)]/20 bg-[color:var(--ps-teal-light)]/60 text-[color:var(--ps-teal-dark)]"
      }`}
    >
      {running ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : error ? (
        <X className="h-3 w-3" />
      ) : (
        <Check className="h-3 w-3" />
      )}
      <Icon className="h-3 w-3" />
      <span>{label}</span>
    </div>
  );
}
