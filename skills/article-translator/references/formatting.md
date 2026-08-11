# Formatting mechanics and special cases

Mechanical rules for keeping a translated document render-identical to the
source, plus special-case playbooks. Read before Phase 4 whenever the source is
anything richer than plain paragraphs.

## Preserving structure and formatting

Translation must not break the document mechanically. Apply these rules across all source formats:

- **Headings.** Translate the text; preserve the heading level (`#`, `##`, `###`).
- **Markdown links** `[text](url)`. Translate the visible text. Leave the URL untouched.
- **Inline code** (`backticks`) and **fenced code blocks** (```` ``` ````). Do not translate. Identifiers, command names, API names, syntax, error messages — verbatim. Translate code comments only when they are clearly authorial prose, not API-style documentation.
- **Tables.** Preserve column structure and alignment markers. Translate cell contents and headers.
- **Blockquotes** (`>`). Preserve the marker. Translate contents.
- **Lists.** Preserve indentation, bullet/number style, and parallel structure across items more rigorously than in flowing prose.
- **Footnote markers** and reference numbers. Keep them linked correctly to their targets.
- **YAML front matter** (`--- ... ---` at the top of Markdown files used by static-site generators). Preserve structure and keys as-is. Translate only the values of user-facing prose fields (`title`, `description`, `summary`, `subtitle`). Never translate: slugs, IDs, dates, tags, layout names, technical flags. When in doubt, leave it.
- **HTML embeds.** Preserve tag structure and attributes. Translate text content between tags. Leave `alt`, `href`, `class`, `id`, `style` alone unless the value is clearly user-facing prose (then translate `alt` and `title`, never `href`/`class`/`id`).
- **Inline emphasis** (`*italic*`, `**bold**`). Preserve the marker placement around the equivalent target-language span.
- **Whitespace and line breaks.** Preserve paragraph breaks exactly. Many publishing pipelines are sensitive to blank-line structure.

When in doubt about a syntactic element, leave it verbatim. Breaking a document's rendering is a worse defect than under-translating an attribute value.

## Special cases

- **Embedded quotations from a third source.** If the quoted text has a canonical published translation in the target language, use it and cite it. Otherwise translate it and mark the passage with a translator's-translation note.
- **Mixed-language source.** If the source already mixes languages (e.g., English technical terms inside a Russian article), preserve the mixing strategy — do not suddenly translate everything into monolingual target. The mixing is part of the style.
- **Headlines, pull quotes, captions.** These often need looser, more idiomatic rendering than body text. Treat them as separate translation problems with their own pragmatic goals.
- **Very long texts (>5000 words).** Build the glossary from the **full** text before translating anything — do not chunk the glossary phase. Then translate in clearly demarcated sections (natural chapters, headings, or 1000–1500-word chunks). Before starting each new chunk: re-read the glossary, and re-read the last paragraph of the previous chunk to lock in cohesion. After every ~1500 words of translation, do a drift check against the glossary — pick three glossary terms and grep the target text so far to confirm they were rendered consistently. A mid-text check catches drift before the end.
