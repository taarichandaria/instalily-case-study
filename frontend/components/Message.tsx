"use client";

import { isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message as MessageT } from "@/lib/types";
import { formatAssistantContent } from "@/lib/formatAssistantContent";
import { PartSectionMedia } from "./PartSectionMedia";
import { ToolBadge } from "./ToolBadge";

type MessageSection = {
  markdown: string;
  parts: MessageT["parts"];
};

type BulletSectionContent = {
  before: string;
  bullets: string[];
  after: string;
};

type SectionPartMatch = {
  part: MessageT["parts"][number];
  matchIndex: number;
  tier: number;
  tieBreaker: number;
};

const PART_NAME_STOPWORDS = new Set([
  "and",
  "for",
  "part",
  "refrigerator",
  "dishwasher",
  "replacement",
  "with",
  "the",
]);

const PS_NUMBER_RE = /PS\d{6,}/i;

function isAccessorySection(markdown: string) {
  return /###\s+(you may also need|related parts|candidate parts)/i.test(
    markdown,
  );
}

function bulletCount(markdown: string) {
  return (markdown.match(/^\s*[-*+]\s+/gm) ?? []).length;
}

function normalizeText(text: string) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function visibleMarkdown(markdown: string) {
  return markdown.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, "$1");
}

function extractPsNumbers(text: string) {
  return [...text.matchAll(/PS\d{6,}/gi)].map(([ps]) => ps.toUpperCase());
}

function matchesPart(content: string, partName: string, psNumber: string) {
  const normalizedPs = normalizeText(psNumber);
  if (normalizedPs && content.includes(normalizedPs)) {
    return true;
  }

  const normalizedName = normalizeText(partName);
  if (normalizedName && content.includes(normalizedName)) {
    return true;
  }

  const meaningfulTokens = normalizedName
    .split(" ")
    .filter((token) => token.length >= 3 && !PART_NAME_STOPWORDS.has(token));
  const matchedTokens = meaningfulTokens.filter((token) => content.includes(token));

  return meaningfulTokens.length >= 2 && matchedTokens.length >= 2;
}

function visibleParts(message: MessageT, content: string) {
  if (message.parts.length === 0) return [];

  const renderedMarkdown = visibleMarkdown(content);
  const renderedPsNumbers = extractPsNumbers(renderedMarkdown);

  // When the assistant explicitly names PS numbers in its final text, those
  // are the canonical parts for this message. Tool calls may have returned
  // other same-named candidates (e.g. multiple "Ice Maker" parts) that were
  // checked and rejected earlier in the turn; don't let them compete with the
  // parts the answer actually mentions.
  if (renderedPsNumbers.length > 0) {
    const psOrder = new Map(
      renderedPsNumbers.map((psNumber, index) => [psNumber, index] as const),
    );
    const psMatched = message.parts
      .filter((part) => psOrder.has(part.ps_number.toUpperCase()))
      .sort(
        (a, b) =>
          (psOrder.get(a.ps_number.toUpperCase()) ?? Number.MAX_SAFE_INTEGER) -
          (psOrder.get(b.ps_number.toUpperCase()) ?? Number.MAX_SAFE_INTEGER),
      );

    if (psMatched.length > 0) {
      return psMatched;
    }
  }

  const normalizedContent = normalizeText(renderedMarkdown);
  const matched = message.parts.filter((part) =>
    matchesPart(normalizedContent, part.name, part.ps_number),
  );

  if (matched.length > 0) {
    return matched;
  }

  return message.parts.length === 1 ? message.parts : [];
}

function splitMarkdownSections(content: string) {
  const trimmed = content.trim();
  if (!trimmed) return [];

  const sections: string[] = [];
  let current: string[] = [];

  for (const line of trimmed.split("\n")) {
    if (/^###\s+/.test(line) && current.some((item) => item.trim() !== "")) {
      sections.push(current.join("\n").trim());
      current = [line];
      continue;
    }
    current.push(line);
  }

  if (current.some((item) => item.trim() !== "")) {
    sections.push(current.join("\n").trim());
  }

  return sections;
}

function splitBulletSection(markdown: string): BulletSectionContent {
  const before: string[] = [];
  const bullets: string[] = [];
  const after: string[] = [];
  let currentBullet: string[] | null = null;
  let sawBullet = false;

  const flushBullet = () => {
    if (!currentBullet) {
      return;
    }
    bullets.push(currentBullet.join("\n").trim());
    currentBullet = null;
  };

  for (const line of markdown.split("\n")) {
    if (/^\s*[-*+]\s+/.test(line)) {
      sawBullet = true;
      flushBullet();
      currentBullet = [line];
      continue;
    }

    if (currentBullet) {
      if (!line.trim() || /^[ \t]+/.test(line)) {
        currentBullet.push(line);
        continue;
      }
      flushBullet();
    }

    if (sawBullet) {
      after.push(line);
    } else {
      before.push(line);
    }
  }

  flushBullet();

  return {
    before: before.join("\n").trim(),
    bullets,
    after: after.join("\n").trim(),
  };
}

function linkFromSection(markdown: string, partName: string, psNumber: string) {
  const links = [...markdown.matchAll(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g)];
  for (const [, label, url] of links) {
    if (matchesPart(normalizeText(label), partName, psNumber)) {
      return url;
    }
  }

  for (const [, , url] of links) {
    if (url.toLowerCase().includes(psNumber.toLowerCase())) {
      return url;
    }
  }

  return null;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function hasExplicitPartMatch(
  markdown: string,
  parts: MessageT["parts"],
) {
  return parts.some(
    (part) => explicitMatchIndex(markdown, part.name, part.ps_number) !== -1,
  );
}

function hasLinkedPartName(
  markdown: string,
  part: MessageT["parts"][number],
) {
  const links = [...markdown.matchAll(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g)];

  return links.some(([, label]) => {
    const normalizedLabel = normalizeText(label);

    return matchesPart(normalizedLabel, part.name, "");
  });
}

function ensurePartLink(
  markdown: string,
  part: MessageT["parts"][number] | undefined,
) {
  if (!part?.source_url) {
    return markdown;
  }

  if (hasLinkedPartName(markdown, part)) {
    return markdown;
  }

  const leadingBoldLabelPattern =
    /(\*\*[^*\n]+\*\*)(?=\s+[–—-]\s+(?:\[[^\]]+\]\([^)]+\)|PS\d{6,}))/;
  if (leadingBoldLabelPattern.test(markdown)) {
    return markdown.replace(leadingBoldLabelPattern, (label) => {
      return `[${label}](${part.source_url})`;
    });
  }

  const boldNamePattern = new RegExp(`\\*\\*${escapeRegExp(part.name)}\\*\\*`);
  if (boldNamePattern.test(markdown)) {
    return markdown.replace(
      boldNamePattern,
      `[**${part.name}**](${part.source_url})`,
    );
  }

  const namePattern = new RegExp(escapeRegExp(part.name));
  if (namePattern.test(markdown)) {
    return markdown.replace(namePattern, `[${part.name}](${part.source_url})`);
  }

  const psPattern = new RegExp(escapeRegExp(part.ps_number));
  if (psPattern.test(markdown)) {
    return markdown.replace(
      psPattern,
      `[${part.ps_number}](${part.source_url})`,
    );
  }

  return markdown;
}

function textFromNode(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }

  if (Array.isArray(node)) {
    return node.map((item) => textFromNode(item)).join(" ");
  }

  if (isValidElement<{ children?: ReactNode }>(node)) {
    return textFromNode(node.props.children);
  }

  return "";
}

function resolvedPartLink(
  parts: MessageT["parts"],
  href: string | undefined,
  children: ReactNode,
) {
  const labelText = textFromNode(children);
  const labelPs = labelText.match(PS_NUMBER_RE)?.[0]?.toUpperCase();
  const hrefPs = href?.match(PS_NUMBER_RE)?.[0]?.toUpperCase();

  // A PS explicit in the visible label is higher-trust than one in the href —
  // if the LLM hallucinates a URL whose PS disagrees with the text, believe
  // the text.
  if (labelPs) {
    const part = parts.find(
      (candidate) =>
        candidate.ps_number.toUpperCase() === labelPs && candidate.source_url,
    );
    if (part?.source_url) {
      return part.source_url;
    }
  }

  const label = normalizeText(labelText);
  if (!label) {
    if (hrefPs) {
      const part = parts.find(
        (candidate) =>
          candidate.ps_number.toUpperCase() === hrefPs && candidate.source_url,
      );
      if (part?.source_url) {
        return part.source_url;
      }
    }
    return href;
  }

  const part = parts.find((candidate) =>
    candidate.source_url
      ? matchesPart(label, candidate.name, candidate.ps_number)
      : false,
  );

  if (part?.source_url) {
    return part.source_url;
  }

  if (hrefPs) {
    const hrefPart = parts.find(
      (candidate) =>
        candidate.ps_number.toUpperCase() === hrefPs && candidate.source_url,
    );
    if (hrefPart?.source_url) {
      return hrefPart.source_url;
    }
  }

  return href;
}

function explicitMatchIndex(markdown: string, partName: string, psNumber: string) {
  const renderedMarkdown = visibleMarkdown(markdown);
  const lowerMarkdown = renderedMarkdown.toLowerCase();
  const lowerPs = psNumber.toLowerCase();
  const psIndex = lowerMarkdown.indexOf(lowerPs);
  if (psIndex !== -1) {
    return psIndex;
  }

  const links = [...markdown.matchAll(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g)];
  for (const [, label] of links) {
    if (matchesPart(normalizeText(label), partName, psNumber)) {
      return lowerMarkdown.indexOf(label.toLowerCase());
    }
  }

  return -1;
}

function exactNameMatchIndex(markdown: string, partName: string) {
  return visibleMarkdown(markdown).toLowerCase().indexOf(partName.toLowerCase());
}

function tokenMatchScore(markdown: string, partName: string) {
  const tokens = normalizeText(partName)
    .split(" ")
    .filter(
      (token) =>
        token.length >= 4 &&
        !PART_NAME_STOPWORDS.has(token) &&
        !/^[a-z]*\d+[a-z\d-]*$/i.test(token),
    );

  if (tokens.length === 0) {
    return 0;
  }

  const normalizedMarkdown = normalizeText(visibleMarkdown(markdown));
  const matchedCount = tokens.filter((token) =>
    normalizedMarkdown.includes(token),
  ).length;

  return matchedCount >= 3 ? matchedCount : 0;
}

function scorePartForSection(
  markdown: string,
  part: MessageT["parts"][number],
): Omit<SectionPartMatch, "part"> | null {
  const explicitIndex = explicitMatchIndex(markdown, part.name, part.ps_number);
  if (explicitIndex !== -1) {
    return {
      matchIndex: explicitIndex,
      tier: 3,
      tieBreaker: 0,
    };
  }

  const exactIndex = exactNameMatchIndex(markdown, part.name);
  if (exactIndex !== -1) {
    return {
      matchIndex: exactIndex,
      tier: 2,
      tieBreaker: 0,
    };
  }

  const score = tokenMatchScore(markdown, part.name);
  if (score === 0) {
    return null;
  }

  return {
    matchIndex: Number.MAX_SAFE_INTEGER,
    tier: 1,
    tieBreaker: score,
  };
}

function assignPartsToBullets(
  bullets: string[],
  parts: MessageT["parts"],
): Array<MessageT["parts"][number] | null> {
  const assigned: Array<MessageT["parts"][number] | null> = bullets.map(
    () => null,
  );
  const claimed = new Set<string>();

  for (const tier of [3, 2] as const) {
    bullets.forEach((bullet, bulletIndex) => {
      if (assigned[bulletIndex]) return;
      const best = parts
        .filter((part) => !claimed.has(part.ps_number))
        .map((part) => {
          const score = scorePartForSection(bullet, part);
          return score && score.tier === tier ? { part, ...score } : null;
        })
        .filter((match): match is SectionPartMatch => match !== null)
        .sort((a, b) => a.matchIndex - b.matchIndex)[0];
      if (best) {
        assigned[bulletIndex] = best.part;
        claimed.add(best.part.ps_number);
      }
    });
  }

  bullets.forEach((bullet, bulletIndex) => {
    if (assigned[bulletIndex]) return;
    const best = parts
      .filter((part) => !claimed.has(part.ps_number))
      .map((part) => {
        const score = scorePartForSection(bullet, part);
        return score && score.tier === 1 ? { part, ...score } : null;
      })
      .filter((match): match is SectionPartMatch => match !== null)
      .sort((a, b) => b.tieBreaker - a.tieBreaker)[0];
    if (best) {
      assigned[bulletIndex] = best.part;
      claimed.add(best.part.ps_number);
    }
  });

  return assigned;
}

function assignPartToBestSection(
  sections: string[],
  part: MessageT["parts"][number],
) {
  let bestSectionIndex = -1;
  let bestMatchIndex = Number.MAX_SAFE_INTEGER;
  let bestTier = -1;
  let bestTieBreaker = -1;

  sections.forEach((markdown, index) => {
    const score = scorePartForSection(markdown, part);
    if (!score) {
      return;
    }

    const sectionPriority = isAccessorySection(markdown)
      ? 2
      : bulletCount(markdown) > 1
        ? 1
        : 0;

    if (score.tier === 3 || score.tier === 2) {
      if (
        bestTier < score.tier ||
        (bestTier === score.tier && score.matchIndex < bestMatchIndex)
      ) {
        bestSectionIndex = index;
        bestMatchIndex = score.matchIndex;
        bestTier = score.tier;
        bestTieBreaker = sectionPriority;
      }
      return;
    }

    if (
      bestTier < 1 ||
      (bestTier === 1 &&
        (score.tieBreaker + sectionPriority > bestTieBreaker ||
          (score.tieBreaker + sectionPriority === bestTieBreaker &&
            index > bestSectionIndex)))
    ) {
      bestSectionIndex = index;
      bestMatchIndex = score.matchIndex;
      bestTier = 1;
      bestTieBreaker = score.tieBreaker + sectionPriority;
    }
  });

  if (bestSectionIndex === -1) {
    return null;
  }

  return {
    sectionIndex: bestSectionIndex,
    matchIndex: bestMatchIndex,
    tier: bestTier,
    tieBreaker: bestTieBreaker,
  };
}

function buildSections(message: MessageT, content: string): MessageSection[] {
  const sections = splitMarkdownSections(content);
  if (sections.length === 0) return [];

  const visible = visibleParts(message, content);
  const groupedMatches: SectionPartMatch[][] = sections.map(() => []);
  const claimed = new Set<string>();

  sections.forEach((markdown, index) => {
    const prioritizedSection =
      isAccessorySection(markdown) ||
      (bulletCount(markdown) > 1 && hasExplicitPartMatch(markdown, visible));
    if (!prioritizedSection) {
      return;
    }

    const limit = Math.max(1, Math.min(3, bulletCount(markdown) || 3));
    const matches = visible
      .filter((part) => !claimed.has(part.ps_number))
      .map((part) => {
        const score = scorePartForSection(markdown, part);
        if (!score) {
          return null;
        }
        return { part, ...score };
      })
      .filter((match): match is SectionPartMatch => match !== null)
      .sort((a, b) => {
        if (a.tier !== b.tier) return b.tier - a.tier;
        if (a.tier >= 2) return a.matchIndex - b.matchIndex;
        return b.tieBreaker - a.tieBreaker;
      })
      .slice(0, limit);

    matches.forEach((match) => {
      groupedMatches[index].push(match);
      claimed.add(match.part.ps_number);
    });
  });

  for (const part of visible) {
    if (claimed.has(part.ps_number)) {
      continue;
    }

    const assignment = assignPartToBestSection(sections, part);
    if (!assignment) {
      continue;
    }
    groupedMatches[assignment.sectionIndex].push({
      part,
      matchIndex: assignment.matchIndex,
      tier: assignment.tier,
      tieBreaker: assignment.tieBreaker,
    });
  }

  return sections.map((markdown, index) => {
    const accessorySection = isAccessorySection(markdown);
    const multiBulletSection = bulletCount(markdown) > 1;
    const limit = accessorySection || multiBulletSection ? 3 : 1;

    const matched = groupedMatches[index]
      .sort((a, b) => {
        if (a.tier !== b.tier) return b.tier - a.tier;
        if (a.tier >= 2) return a.matchIndex - b.matchIndex;
        return b.tieBreaker - a.tieBreaker;
      })
      .slice(0, limit)
      .map(({ part }) => ({
        ...part,
        source_url:
          part.source_url ?? linkFromSection(markdown, part.name, part.ps_number),
      }));

    return { markdown, parts: matched };
  });
}

function createMarkdownComponents(parts: MessageT["parts"]) {
  return {
    a: (props: React.ComponentProps<"a">) => (
      <a
        {...props}
        href={resolvedPartLink(parts, props.href, props.children)}
        target="_blank"
        rel="noopener noreferrer"
      />
    ),
  };
}

export function Message({ message }: { message: MessageT }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-none bg-[color:var(--ps-teal)] px-4 py-2.5 text-white text-[15px] leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  const content = formatAssistantContent(message.content);
  const linkableParts = visibleParts(message, content);
  const sections = buildSections(message, content);

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        {message.tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.tools.map((t) => (
              <ToolBadge key={t.id} activity={t} />
            ))}
          </div>
        )}
        {(message.content.length > 0 || message.streaming) && (
          <div className="assistant-message rounded-sm border border-[color:var(--border)] px-5 py-4 text-[15px] text-[color:var(--foreground)] shadow-sm">
            {sections.length > 0 ? (
              <div className="space-y-4">
                {sections.map((section, index) => {
                  const hasBulletList = bulletCount(section.markdown) > 1;
                  const splitBullets = hasBulletList
                    ? splitBulletSection(section.markdown)
                    : null;
                  const bulletPartAssignments =
                    splitBullets && splitBullets.bullets.length > 0
                      ? assignPartsToBullets(
                          splitBullets.bullets,
                          linkableParts,
                        )
                      : [];
                  const assignedBulletParts = bulletPartAssignments.filter(
                    (part): part is MessageT["parts"][number] => part !== null,
                  );
                  const inlineListMedia =
                    hasBulletList && assignedBulletParts.length > 0;
                  const markdownComponents = createMarkdownComponents(
                    section.parts.length > 0 ? section.parts : linkableParts,
                  );
                  const bulletSection = inlineListMedia ? splitBullets : null;

                  return (
                    <div
                      key={`${index}-${section.markdown.slice(0, 24)}`}
                      className={
                        section.parts.length > 0 && !inlineListMedia
                          ? "flex flex-col gap-3 md:flex-row md:items-start md:gap-5"
                          : ""
                      }
                    >
                      <div className="min-w-0 flex-1">
                        {bulletSection ? (
                          <div className="space-y-3">
                            {bulletSection.before && (
                              <div className="prose prose-sm max-w-none font-sans">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={markdownComponents}
                                >
                                  {bulletSection.before}
                                </ReactMarkdown>
                              </div>
                            )}
                            <div className="not-prose space-y-3">
                              {bulletSection.bullets.map((bullet, bulletIndex) => {
                                const bulletPart =
                                  bulletPartAssignments[bulletIndex] ?? null;
                                return (
                                  <div
                                    key={`${index}-bullet-${bulletIndex}`}
                                    className="flex flex-col gap-3 md:flex-row md:items-start md:gap-4"
                                  >
                                    <div className="min-w-0 flex-1">
                                      <div className="prose prose-sm max-w-none font-sans">
                                        <ReactMarkdown
                                          remarkPlugins={[remarkGfm]}
                                          components={createMarkdownComponents(
                                            bulletPart
                                              ? [
                                                  bulletPart,
                                                  ...linkableParts.filter(
                                                    (p) =>
                                                      p.ps_number !==
                                                      bulletPart.ps_number,
                                                  ),
                                                ]
                                              : linkableParts,
                                          )}
                                        >
                                          {ensurePartLink(bullet, bulletPart ?? undefined)}
                                        </ReactMarkdown>
                                      </div>
                                    </div>
                                    {bulletPart && (
                                      <div className="md:shrink-0 md:pt-1">
                                        <PartSectionMedia parts={[bulletPart]} />
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            {bulletSection.after && (
                              <div className="prose prose-sm max-w-none font-sans">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={markdownComponents}
                                >
                                  {bulletSection.after}
                                </ReactMarkdown>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="prose prose-sm max-w-none font-sans">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={markdownComponents}
                            >
                              {ensurePartLink(
                                section.markdown,
                                section.parts.length === 1
                                  ? section.parts[0]
                                  : undefined,
                              )}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                      {section.parts.length > 0 && !inlineListMedia && (
                        <div className="md:shrink-0">
                          <PartSectionMedia parts={section.parts} />
                        </div>
                      )}
                    </div>
                  );
                })}
                {message.streaming && message.content.length > 0 && (
                  <span className="stream-cursor" />
                )}
              </div>
            ) : (
              <div
                className={`prose prose-sm max-w-none font-sans ${message.streaming ? "stream-cursor" : ""}`}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
