// Render the assistant's paragraphs, emphasis and steps with React escaping.
// Model output is never treated as HTML or as executable links.
import { publicWebUrl } from "./SearchImageGallery";
type Source = { title: string; url: string };
function inline(text: string, sources: Source[]) {
  return text
    .split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[\d{1,2}\])/g)
    .map((part, i) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : /^\[\d{1,2}\]$/.test(part) &&
        sources[Number(part.slice(1, -1)) - 1] &&
        publicWebUrl(sources[Number(part.slice(1, -1)) - 1].url) ? (
        <a
          className="rafinha-inline-citation"
          key={i}
          href={sources[Number(part.slice(1, -1)) - 1].url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Fonte: ${sources[Number(part.slice(1, -1)) - 1].title}`}
        >
          {part}
        </a>
      ) : part.startsWith("*") && part.endsWith("*") ? (
        <em key={i}>{part.slice(1, -1)}</em>
      ) : (
        part
      ),
    );
}

export function RafinhaMessageText({
  text,
  sources = [],
}: {
  text: string;
  sources?: Source[];
}) {
  type Block = { kind: "p" | "ol" | "ul"; lines: string[] };
  const blocks: Block[] = [];
  let current: Block = { kind: "p", lines: [] };
  function flush() {
    if (current.lines.length) blocks.push(current);
    current = { kind: "p", lines: [] };
  }
  for (const line of text.split("\n")) {
    if (!line.trim()) {
      flush();
      continue;
    }
    const ordered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const unordered = line.match(/^\s*[-•*]\s+(.*)$/);
    const kind = ordered ? "ol" : unordered ? "ul" : "p";
    if (current.kind !== kind) {
      flush();
      current = { kind, lines: [] };
    }
    current.lines.push(
      ordered?.[1] || unordered?.[1] || line.replace(/^#{1,3}\s+/, ""),
    );
  }
  flush();
  return (
    <div className="rafinha-rich-text">
      {blocks.map((block, i) => {
        if (block.kind === "p")
          return <p key={i}>{inline(block.lines.join("\n"), sources)}</p>;
        const List = block.kind;
        return (
          <List key={i}>
            {block.lines.map((line, j) => (
              <li key={j}>{inline(line, sources)}</li>
            ))}
          </List>
        );
      })}
    </div>
  );
}
