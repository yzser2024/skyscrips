/**
 * Apply the relay fingerprint rules to assembled prompt text.
 *
 * The gateway scans the `system`, `developer` and `assistant` roles and also
 * scans tool descriptions. In this harness every fingerprint that reaches the
 * wire lives in the assembled system sections — the shipped tool declarations
 * carry none — so the assembly is the surface this module rewrites, and one
 * transform covers what a per-file edit would have had to chase section by
 * section.
 *
 * The transform is pure and idempotent: text without a fingerprint comes back
 * unchanged, and sanitizing already-sanitized text changes nothing further.
 *
 * @module @deepseek-ai/dsh-relay-sanitizer
 */

import type { PromptPresentation } from '@deepseek-ai/dsh-system-prompt'
import {
  BARE_AT, BARE_AT_REPLACEMENT, CONTROL_TOKENS, IDENTITY_RULES, MARKER_RULES,
  PHRASE_RULES, PREFIX_RULES, type MarkerRule,
} from './rules.ts'

/** Options the transform accepts. */
export interface SanitizeOptions {
  /**
   * Rewrite phrase-level n-grams. A gateway matches these empirically and they
   * are the one category whose rewording the model can notice; a deployment
   * that talks to the official API instead of a relay switches them off.
   */
  phrases?: boolean
}

/** What one sanitize pass changed; the plugin logs it and tests assert on it. */
export interface SanitizeReport {
  /** Literal fingerprint substitutions. */
  readonly markers: number
  /** Opening fingerprints rewritten. */
  readonly prefixes: number
  /** Control tokens removed. */
  readonly tokens: number
  /** Phrase-level n-grams rewritten. */
  readonly phrases: number
  /** Identity declarations folded. */
  readonly identities: number
  /** Bare at-signs replaced with the full-width form. */
  readonly atSigns: number
  /** Sections whose text changed. */
  readonly sections: number
  /** True when anything changed at all. */
  readonly changed: boolean
}

/** Which counter a rule category increments. */
type Counter = 'markers' | 'prefixes' | 'tokens' | 'phrases' | 'identities' | 'atSigns'

/**
 * Mutable accumulator the transforms write into; one per assembly.
 * @internal
 */
export class Tally {
  markers = 0
  prefixes = 0
  tokens = 0
  phrases = 0
  identities = 0
  atSigns = 0
  sections = 0

  /** @returns the immutable report for this pass. */
  report(): SanitizeReport {
    return {
      markers: this.markers,
      prefixes: this.prefixes,
      tokens: this.tokens,
      phrases: this.phrases,
      identities: this.identities,
      atSigns: this.atSigns,
      sections: this.sections,
      changed: this.markers + this.prefixes + this.tokens + this.phrases
        + this.identities + this.atSigns + this.sections > 0,
    }
  }
}

/**
 * Replace every case-insensitive occurrence of one rule's marker.
 * @param text - the text to rewrite.
 * @param rule - the marker and its replacement.
 * @param tally - the accumulator to increment.
 * @param counter - which counter to increment.
 * @returns the rewritten text, or the input when nothing matched.
 */
function applyRule(text: string, rule: MarkerRule, tally: Tally, counter: Counter): string {
  if (rule.marker.length === 0) return text
  if (!text.toLowerCase().includes(rule.marker.toLowerCase())) return text
  // The escape keeps a marker's regex metacharacters from widening the pattern.
  const pattern = new RegExp(rule.marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
  const found = text.match(pattern)
  if (found === null) return text
  tally[counter] += found.length
  return text.replace(pattern, () => rule.replacement)
}

/**
 * Remove ChatML and role-wrapper tokens, keeping the visible text around them.
 * The gateway rejects a request carrying one of these outright; the instruction
 * around it is what the model has to read.
 * @param text - the text to rewrite.
 * @param tally - the accumulator to increment.
 * @returns the text without control tokens.
 */
function stripTokens(text: string, tally: Tally): string {
  let out = text
  for (const token of CONTROL_TOKENS) {
    if (!out.includes(token)) continue
    tally.tokens += out.split(token).length - 1
    out = out.split(token).join('')
  }
  return out
}

/**
 * Rewrite one run of model-visible text.
 * @param text - the text to rewrite.
 * @param tally - the accumulator to increment.
 * @param usePhrases - whether the phrase-level n-gram rules apply.
 * @returns the rewritten text.
 */
export function sanitizeText(text: string, tally: Tally, usePhrases = true): string {
  if (text.length === 0) return text
  let out = stripTokens(text, tally)
  for (const rule of MARKER_RULES) out = applyRule(out, rule, tally, 'markers')
  if (usePhrases) {
    for (const rule of PHRASE_RULES) out = applyRule(out, rule, tally, 'phrases')
  }
  if (out.includes(BARE_AT)) {
    tally.atSigns += out.split(BARE_AT).length - 1
    out = out.split(BARE_AT).join(BARE_AT_REPLACEMENT)
  }
  // Folding runs after the phrase rules so a marker naming the identity cannot
  // be reassembled from two separately folded halves.
  for (const rule of IDENTITY_RULES) out = applyRule(out, rule, tally, 'identities')
  // An opening fingerprint binds at offset 0, but an empty leading section can
  // put it anywhere in the prompt; rewriting it wherever it lands keeps the
  // result independent of section order.
  for (const rule of PREFIX_RULES) out = applyRule(out, rule, tally, 'prefixes')
  return out
}

/**
 * Rewrite an assembled prompt presentation in place.
 *
 * Sections are sanitized before the caller renders them, so the text the model
 * reads already lacks every fingerprint. Only text changes: a section's name,
 * order, and interpolation flag are untouched, so logged-prompt replay still
 * matches by name.
 *
 * @param assembly - the presentation to rewrite; its sections are mutated.
 * @param settings - the optional rule switches.
 * @returns the report for this pass.
 */
export function sanitizePresentation(
  assembly: PromptPresentation,
  settings: SanitizeOptions = {},
): SanitizeReport {
  const usePhrases = settings.phrases ?? true
  const tally = new Tally()
  for (const section of assembly.sections) {
    const before = section.text
    const after = sanitizeText(before, tally, usePhrases)
    if (after === before) continue
    section.text = after
    tally.sections += 1
  }
  return tally.report()
}
