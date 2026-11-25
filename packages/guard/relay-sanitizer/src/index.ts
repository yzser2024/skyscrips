/**
 * Relay fingerprint sanitizer: strip the content fingerprints a local relay
 * reads as evidence of a non-official client from every assembled system prompt.
 *
 * It hooks `system-prompt/assemble`, the waterfall every prompt assembly passes
 * through, and rewrites the section text before the caller renders it. Hooking
 * the assembly rather than each contributing section means one transform covers
 * the armor text, the harness identity opener, the tool guidance, and the
 * file-reference paragraph together — including the text a deployment adds
 * later, which no shipped section owns.
 *
 * The session log keeps the assembled-and-sanitized text, so replay and
 * compaction read exactly what the model read.
 *
 * @module @deepseek-ai/dsh-relay-sanitizer
 */

import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-system-prompt'
import z from '@deepseek-ai/schemastery'
import { sanitizePresentation, type SanitizeOptions, type SanitizeReport } from './sanitize.ts'

/** Stable Cordis plugin name. */
export const name = 'relay-sanitizer'

/** The prompt registry this plugin participates in. */
export const inject = ['systemPrompt']

/** Configuration for {@link apply}. */
export interface Config {
  /**
   * Log one line per assembly that changed, naming the rule categories that
   * fired. Off by default: the counts repeat every turn, so the log is a
   * debugging aid rather than a running record.
   */
  logRewrites?: boolean
  /**
   * Rewrite the phrase-level n-grams. These are fingerprints a gateway matches
   * inside a longer sentence, measured against a local relay; a deployment that
   * talks to the official API switches them off so its prompt stays
   * byte-identical.
   */
  phrases?: boolean
}

export const Config: z<Config> = z.object({
  logRewrites: z.boolean().default(false),
  phrases: z.boolean().default(true),
})

/**
 * Hook the assembly waterfall and rewrite every fingerprint it carries.
 * @param ctx - plugin context with the `systemPrompt` registry.
 * @param config - validated plugin configuration.
 */
export function apply(ctx: Context, config: Config): void {
  const settings: SanitizeOptions = {
    phrases: config.phrases ?? true,
  }
  const logRewrites = config.logRewrites ?? false

  // Prepended so the rewrite runs before any listener that reads the rendered
  // text, and after the registry has resolved every section.
  ctx.on('system-prompt/assemble', async (_assembly, context, next) => {
    const assembly = await next()
    context.signal?.throwIfAborted()
    const report = sanitizePresentation(assembly, settings)
    if (report.changed && logRewrites) logRewrite(report)
    return assembly
  }, { prepend: true })
}

/**
 * Emit one summary line for a rewritten assembly.
 * @param report - the counts from the sanitize pass.
 */
function logRewrite(report: SanitizeReport): void {
  const fired = Object.entries(report)
    .filter(([key, value]) => key !== 'changed' && typeof value === 'number' && value > 0)
    .map(([key, value]) => `${key}=${String(value)}`)
  console.warn(`[relay-sanitizer] rewrote prompt: ${fired.join(' ')}`)
}
