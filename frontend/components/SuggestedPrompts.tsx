"use client";

import { Sparkles } from "lucide-react";

const PROMPTS = [
  "How can I install part number PS11752778?",
  "Is part PS11752778 compatible with my WDT780SAEM1 dishwasher?",
  "The ice maker on my Whirlpool fridge isn't making ice. What part do I need?",
  "My dishwasher WDT780SAEM1 isn't draining — help me diagnose and install the fix.",
];

export function SuggestedPrompts({ onPick }: { onPick: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-12 gap-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--ps-teal-light)]">
          <Sparkles className="h-6 w-6 text-[color:var(--ps-teal)]" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-[color:var(--foreground)]">
            PartSelect Assistant
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Refrigerator &amp; dishwasher parts — search, diagnose, install.
          </p>
        </div>
      </div>
      <div className="grid gap-2 w-full max-w-xl">
        {PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => onPick(p)}
            className="text-left px-4 py-3 rounded-xl border border-[color:var(--border)] bg-white hover:border-[color:var(--ps-teal)] hover:bg-[color:var(--ps-teal-light)]/40 transition-colors text-sm text-[color:var(--foreground)]"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
