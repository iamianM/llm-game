export const MAX_BUBBLE_CHARS = 180;

export function paginate(text: string, maxChars: number = MAX_BUBBLE_CHARS): string[] {
  const clean = text.trim();
  if (!clean) return [];
  const pages: string[] = [];
  for (const paragraph of clean.split("\n\n").map((item) => item.trim()).filter(Boolean)) {
    const sentences = splitSentences(paragraph);
    let page = "";
    for (const sentence of sentences) {
      if (!page) {
        if (sentence.length <= maxChars) page = sentence;
        else pages.push(...splitLongSentence(sentence, maxChars));
        continue;
      }
      const next = `${page} ${sentence}`;
      if (next.length <= maxChars) {
        page = next;
      } else {
        pages.push(page);
        if (sentence.length <= maxChars) page = sentence;
        else {
          pages.push(...splitLongSentence(sentence, maxChars));
          page = "";
        }
      }
    }
    if (page) pages.push(page);
  }
  return pages.filter(Boolean);
}

function splitSentences(text: string): string[] {
  const sentences: string[] = [];
  let start = 0;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if ((char === "." || char === "!" || char === "?") && (!next || next === " ")) {
      sentences.push(text.slice(start, index + 1).trim());
      start = index + 1;
    }
  }
  const tail = text.slice(start).trim();
  if (tail) sentences.push(tail);
  return sentences.length ? sentences : [text];
}

function splitLongSentence(text: string, maxChars: number): string[] {
  const pages: string[] = [];
  let remaining = text.trim();
  while (remaining.length > maxChars) {
    const cut = bestBreakIndex(remaining, maxChars);
    pages.push(remaining.slice(0, cut).trim());
    remaining = remaining.slice(cut).trim();
  }
  if (remaining) pages.push(remaining);
  return pages;
}

function bestBreakIndex(text: string, maxChars: number): number {
  for (let index = maxChars; index > Math.max(0, maxChars - 56); index -= 1) {
    const char = text[index];
    if (char === "," || char === ";" || char === " ") return index + (char === " " ? 0 : 1);
  }
  return maxChars;
}
