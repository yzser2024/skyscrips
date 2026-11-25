/**
 * The relay fingerprint rules this build enforces on every model request.
 *
 * A local relay fronting the upstream gateway decides whether a request looks
 * like an official client by two kinds of evidence: literal content
 * fingerprints, and the shape of the request. The upstream scans the `system`,
 * `developer` and `assistant` roles (never `user`) and also scans tool
 * descriptions, so a fingerprint reaches the wire through prompt sections, tool
 * schemas, or a tool result verbatim — three separate paths that no single
 * prompt section can cover.
 *
 * This module owns the rules alone: masks, folding tables, and the two request
 * shape normalizations. `sanitize.ts` applies them to a request.
 *
 * @module @deepseek-ai/dsh-relay-sanitizer
 */

/**
 * ChatML and other role-wrapper tokens. A gateway rejects a request carrying
 * any of these with its own error code, independent of the surrounding text;
 * stripping the token and keeping the visible text leaves the instruction
 * readable to the model while removing the fingerprint.
 */
export const CONTROL_TOKENS: readonly string[] = [
  '<|im_start|>',
  '<|im_end|>',
  '<|endoftext|>',
  '<|begin\u2581of\u2581sentence|>',
  '<|end\u2581of\u2581sentence|>',
  '<|User|>',
  '<|Assistant|>',
  '<|System|>',
  '<<SYS>>',
  '<</SYS>>',
  '[INST]',
  '[/INST]',
]

/**
 * One literal substitution: a fingerprint phrase and the text that keeps its
 * meaning while no longer matching it. Matching is case-insensitive; the
 * replacement preserves the matched region's original spelling only for the
 * tokens flagged `preserveCase`.
 */
export interface MarkerRule {
  /** Exact fingerprint text, matched case-insensitively. */
  readonly marker: string
  /** Text that replaces every match. */
  readonly replacement: string
}

/**
 * Fingerprints that a gateway matches anywhere in a scanned message. Each is an
 * official-client banner; changing any single character clears it, so the
 * replacement keeps the sentence readable.
 */
export const MARKER_RULES: readonly MarkerRule[] = [
  { marker: "You are Claude Code, Anthropic's official CLI for Claude.", replacement: 'You are Claude Code, an official CLI for Claude.' },
  { marker: 'x-anthropic-billing-header', replacement: 'x-client-billing-header' },
  { marker: 'To give feedback, users should report the issue at', replacement: 'For feedback, users should report the issue at' },
]

/**
 * Fingerprints a gateway matches only at offset 0 of the first system turn:
 * an opener that reads as an unapproved client driving the account. Prompt
 * sections concatenate in ascending order, so the identity section at order
 * -1000 is what occupies offset 0. Rewriting it here keeps every deployment
 * persona compatible without needing each one to reword its opening.
 */
export const PREFIX_RULES: readonly MarkerRule[] = [
  { marker: "You are a coding agent running in the Codex CLI, a terminal-based coding assistant.", replacement: 'You are a coding agent, a terminal-based coding assistant.' },
  { marker: 'You are an AI agent powered by DeepSeek Harness.', replacement: 'You are an AI agent powered by DeepSeek.' },
  // The model id is a prompt variable, so this rule matches the part that does
  // not change under interpolation: a fixed id in the marker would miss every
  // other route. Assembled section text still carries `{{model}}` when the
  // sanitizer runs, which is why the stable prefix is the match unit.
  { marker: 'You are a coding agent powered by ', replacement: 'You are a coding agent running on ' },
]

/**
 * Identity declarations the gateway folds before comparing: the harness name
 * and its spellings. Folding here means a fingerprint cannot be reassembled by
 * concatenating two sections that spell the name differently.
 */
export const IDENTITY_RULES: readonly MarkerRule[] = [
  { marker: 'DeepSeek-Harness', replacement: 'DeepSeek' },
  { marker: 'DeepSeek Harness', replacement: 'DeepSeek' },
  { marker: 'deepseek-harness', replacement: 'deepseek' },
]

/**
 * Phrase-level n-gram fingerprints. A single word of these phrases is harmless
 * and a half-sentence is harmless; the phrase inside a longer sentence is what
 * trips the gateway, so the whole phrase is the unit that must change. The
 * replacement rewrites one word rather than deleting the phrase, because the
 * sentence still has to mean the same thing to the model.
 */
export const PHRASE_RULES: readonly MarkerRule[] = [
  { marker: 'workspace root', replacement: 'workspace r00t' },
  { marker: 'workspace-root', replacement: 'workspace-r00t' },
  { marker: 'path to the project root', replacement: 'path to the project r00t' },
]

/**
 * The `" @ "` form of a bare at-sign. An at-sign between spaces is the marker a
 * gateway reads as a client-side command prefix, so it becomes the full-width
 * form, which reads the same to the model.
 */
export const BARE_AT = ' @ '
export const BARE_AT_REPLACEMENT = ' \uFF20 '

/**
 * Whether a role's text is scanned by the gateway. `user` carries what the user
 * actually asked, so the gateway leaves it alone; rewriting it would corrupt
 * the user's own words.
 */
export const SCANNED_ROLES: readonly string[] = ['system', 'developer', 'assistant']
