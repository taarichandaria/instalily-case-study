const STRUCTURED_MARKDOWN_LINE =
  /^\s*(#{1,6}\s|[-*+]\s|>\s|\d+\.\s|```|~~~|\|.+\|)/m;

const PS_NUMBER_PATTERN = /PS\d{6,}/i;

type LineType = "blank" | "heading" | "bullet" | "paragraph";

function hasStructuredMarkdown(content: string) {
  return STRUCTURED_MARKDOWN_LINE.test(content);
}

function isHeadingLine(line: string) {
  const clean = line.replace(/:$/, "").trim();

  if (!clean || clean.length < 3 || clean.length > 48) return false;
  if (PS_NUMBER_PATTERN.test(clean)) return false;
  if (/[.!?]$/.test(clean)) return false;
  if (/https?:\/\//i.test(clean)) return false;
  if (/[*_[\]()`]/.test(clean)) return false;
  if (!/^[A-Za-z][A-Za-z0-9'&/ -]+$/.test(clean)) return false;

  const words = clean.split(/\s+/);
  if (words.length > 6) return false;

  return (
    /:$/.test(line) ||
    /steps|installation|compatibility|troubleshooting|safety|overview/i.test(
      clean,
    ) ||
    words.length <= 4
  );
}

function formatPsToken(token: string) {
  const linked = token.match(/^\[([^\]]+)\]\((.+)\)$/);

  if (linked) {
    return `[**${linked[1]}**](${linked[2]})`;
  }

  return `**${token}**`;
}

function maybeBold(text: string) {
  const trimmed = text.trim();
  return trimmed.includes("**") ? trimmed : `**${trimmed}**`;
}

function formatPartBullet(line: string) {
  if (!PS_NUMBER_PATTERN.test(line)) return null;

  const match =
    line.match(
      /^(.+?)\s+[–—-]\s+((?:\[[^\]]+\]\([^)]+\)|PS\d{6,}))(.*)$/i,
    ) ??
    line.match(
      /^(.+?)\s*:\s*((?:\[[^\]]+\]\([^)]+\)|PS\d{6,}))(.*)$/i,
    );

  if (!match) return null;

  const [, rawName, rawPs, rawRest] = match;
  const name = maybeBold(rawName);
  const ps = formatPsToken(rawPs.trim());
  const rest = rawRest
    .trim()
    .replace(/^[:\s·-–—]+/, "")
    .trim();

  return `- ${name} — ${ps}${rest ? ` · ${rest}` : ""}`;
}

function pushLine(
  output: string[],
  previousType: LineType | null,
  nextType: LineType,
  text: string,
) {
  const needsSpacer =
    output.length > 0 &&
    output.at(-1) !== "" &&
    !(
      (previousType === "heading" && nextType !== "heading") ||
      (previousType === "bullet" && nextType === "bullet")
    );

  if (needsSpacer) {
    output.push("");
  }

  output.push(text);
}

export function formatAssistantContent(content: string) {
  const normalized = content.replace(/\r\n?/g, "\n").trim();

  if (!normalized || hasStructuredMarkdown(normalized)) {
    return content;
  }

  const output: string[] = [];
  let previousType: LineType | null = null;

  for (const rawLine of normalized.split("\n")) {
    const line = rawLine.trim();

    if (!line) {
      if (output.at(-1) !== "") {
        output.push("");
      }
      previousType = "blank";
      continue;
    }

    const partBullet = formatPartBullet(line);

    if (partBullet) {
      pushLine(output, previousType, "bullet", partBullet);
      previousType = "bullet";
      continue;
    }

    if (isHeadingLine(line)) {
      pushLine(output, previousType, "heading", `### ${line.replace(/:$/, "")}`);
      previousType = "heading";
      continue;
    }

    pushLine(output, previousType, "paragraph", line);
    previousType = "paragraph";
  }

  return output.join("\n").replace(/\n{3,}/g, "\n\n");
}
