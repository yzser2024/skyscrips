---
description: "Strips the content fingerprints a local relay reads as evidence of a non-official client from every assembled system prompt."
kind: "package-reference"
---

# @deepseek-ai/dsh-relay-sanitizer

Keeps the assembled system prompt free of the content fingerprints a local relay reads as evidence that a non-official client sent the request.

A relay fronting the upstream gateway decides that question from two kinds of evidence: literal content fingerprints, and the shape of the request. The upstream scans the `system`, `developer` and `assistant` roles and also scans tool descriptions, so a fingerprint reaches the wire through the prompt, the tool schemas, or a message already committed to the log — three separate paths that no single prompt section covers.

This plugin takes the first path. It hooks `system-prompt/assemble`, the waterfall every prompt assembly passes through, and rewrites section text before the caller renders it. Because it rewrites the assembly rather than the sections that contributed to it, one transform covers the armor text, the harness identity opener, the tool-guidance paragraphs, and any section a deployment adds later.

## Configuration

```yaml
- id: relay-sanitizer
  name: '@deepseek-ai/dsh-relay-sanitizer'
  config:
    logRewrites: false
    phrases: true
```

| Field | Default | Meaning |
|---|---|---|
| `logRewrites` | `false` | Log one line per rewritten assembly, naming the rule categories that fired. The counts repeat every turn, so this is a debugging aid. |
| `phrases` | `true` | Rewrite the phrase-level n-grams. Switch it off when talking to the official API rather than a relay, so the prompt stays byte-identical. |

## Rules

The rule tables live in `src/rules.ts` and carry the reason for each entry.

| Category | Applies to | Effect |
|---|---|---|
| Control tokens | assembly text | ChatML and role-wrapper tokens (`<\|im_start\|>`, `<\|endoftext\|>`, `[INST]`, …) are removed; the visible instruction around them stays. A gateway rejects a request carrying one outright. |
| Markers | assembly text | Three official-client banners are reworded so the sentence still reads the same. A gateway matches these anywhere in a scanned message. |
| Opening fingerprints | assembly text | The harness identity opener and two other client openers are reworded. A gateway matches these at offset 0, which is the section ordered at `HARNESS_IDENTITY`. |
| Identity declarations | assembly text | `DeepSeek Harness` and its spellings fold to `DeepSeek`. Folding runs after the phrase rules so a marker naming the identity cannot be reassembled from two separately folded halves. |
| Phrase n-grams | assembly text | `workspace root` becomes `workspace r00t`. A gateway matches this phrase inside a longer sentence while the bare word or a half sentence passes, so the phrase is the unit that must change. |
| Bare at-sign | assembly text | `" @ "` becomes the full-width form, which reads the same to the model. |

The `user` role is never rewritten. It carries what the user actually asked, and the gateway does not scan it.

## Model Experience

The sanitized text is what the session log records, so replay and compaction read exactly what the model read, and a resumed session does not re-render a different prompt than the one it was billed for. The transform is idempotent: sanitizing text that is already sanitized changes nothing, so a prompt rebuilt from the log is stable.

Every rule is a literal substitution, which means a rejected request whose text came from operator prose — a document, a tool result quoted into a prompt — is repaired the same way a shipped section is. The cost is one scan of the assembly per turn.

## Known Limitations and Deferred Work

- Message text outside the system prompt is not rewritten. A fingerprint a user pastes into a `user` turn reaches the wire unchanged, by design: rewriting the user's own words is a content change the gateway does not require.
- The rule tables encode what a gateway was measured to match. A gateway that adds a fingerprint needs a new entry; nothing infers one.
- Request shape (a string `tool_choice`, the absent `reasoning_effort: "off"`, `tools` dropped under `tool_choice: "none"`) belongs to the adapter that serializes the request, not to this plugin.
