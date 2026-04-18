"use client";

import type { PartPreview } from "@/lib/types";

export function PartSectionMedia({ parts }: { parts: PartPreview[] }) {
  return (
    <div className="not-prose grid grid-cols-1 gap-2 sm:grid-cols-2 md:w-[148px] md:grid-cols-1">
      {parts.map((part) => {
        const image = (
          <div className="overflow-hidden rounded-sm border border-[color:var(--border)] bg-[#fbfdfd] shadow-[0_6px_18px_rgba(17,24,39,0.05)] transition-colors hover:border-[color:var(--ps-teal)]/45">
            <div className="aspect-[4/3] overflow-hidden bg-white">
              <img
                src={part.image_url}
                alt={part.name}
                loading="lazy"
                className="h-full w-full object-contain p-3"
              />
            </div>
          </div>
        );

        if (!part.source_url) {
          return <div key={part.ps_number}>{image}</div>;
        }

        return (
          <a
            key={part.ps_number}
            href={part.source_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open ${part.name} on PartSelect`}
            className="block"
          >
            {image}
          </a>
        );
      })}
    </div>
  );
}
