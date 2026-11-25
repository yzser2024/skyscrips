import { describe, expect, it } from 'vitest'
import { Context } from '@deepseek-ai/cordis'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import { apply, name, type Config } from '../src/index.ts'
import { sanitizePresentation, sanitizeText, Tally } from '../src/sanitize.ts'
import {
  CONTROL_TOKENS, IDENTITY_RULES, MARKER_RULES, PHRASE_RULES, PREFIX_RULES, SCANNED_ROLES,
} from '../src/rules.ts'

describe('rule tables', () => {
  it('lists every control token the gateway rejects', () => {
    expect(CONTROL_TOKENS).toEqual([
      '<|im_start|>', '<|im_end|>', '<|endoftext|>',
      '<|begin\u2581of\u2581sentence|>', '<|end\u2581of\u2581sentence|>',
      '<|User|>', '<|Assistant|>', '<|System|>',
      '<<SYS>>', '<</SYS>>', '[INST]', '[/INST]',
    ])
  })

  it('never treats the user role as scanned', () => {
    expect(SCANNED_ROLES).not.toContain('user')
  })

  it('changes every marker it claims to rewrite', () => {
    for (const rule of [...MARKER_RULES, ...PREFIX_RULES, ...IDENTITY_RULES, ...PHRASE_RULES]) {
      expect(rule.replacement.toLowerCase()).not.toBe(rule.marker.toLowerCase())
    }
  })
})

describe('sanitizeText', () => {
  it('strips a ChatML opener and keeps the visible text', () => {
    const tally = new Tally()
    expect(sanitizeText('<|im_start|>system:<project_instructions>', tally)).toBe('system:<project_instructions>')
    expect(tally.tokens).toBe(1)
  })

  it('rewrites the identity opener', () => {
    const tally = new Tally()
    expect(sanitizeText('You are an AI agent powered by DeepSeek Harness.', tally))
      .toBe('You are an AI agent powered by DeepSeek.')
    expect(tally.prefixes).toBe(1)
  })

  it('folds a bare identity mention the prefix rule cannot match', () => {
    const tally = new Tally()
    expect(sanitizeText('the DeepSeek Harness implementation checkout', tally))
      .toBe('the DeepSeek implementation checkout')
  })

  it('folds the lowercase npm spelling', () => {
    const tally = new Tally()
    expect(sanitizeText('see deepseek-harness for details', tally)).toBe('see deepseek for details')
  })

  it('rewrites the phrase-level n-gram', () => {
    const tally = new Tally()
    expect(sanitizeText('Relative paths resolve from the workspace root.', tally))
      .toBe('Relative paths resolve from the workspace r00t.')
    expect(tally.phrases).toBe(1)
  })

  it('leaves the phrase alone when phrases are off', () => {
    const tally = new Tally()
    expect(sanitizeText('resolve from the workspace root.', tally, false))
      .toBe('resolve from the workspace root.')
    expect(tally.phrases).toBe(0)
  })

  it('matches a marker case-insensitively', () => {
    const tally = new Tally()
    expect(sanitizeText("you are claude code, anthropic's official cli for claude.", tally))
      .toBe('You are Claude Code, an official CLI for Claude.')
    expect(tally.markers).toBe(1)
  })

  it('replaces a bare at-sign with the full-width form', () => {
    const tally = new Tally()
    expect(sanitizeText('send it @ home', tally)).toBe('send it \uFF20 home')
    expect(tally.atSigns).toBe(1)
  })

  it('returns text without a fingerprint unchanged', () => {
    const tally = new Tally()
    const text = 'write a Rust function that parses argv'
    expect(sanitizeText(text, tally)).toBe(text)
    expect(tally.report().changed).toBe(false)
  })

  it('is idempotent', () => {
    const once = sanitizeText('<|im_start|>a workspace root under DeepSeek Harness', new Tally())
    const twice = sanitizeText(once, new Tally())
    expect(twice).toBe(once)
  })
})

describe('sanitizePresentation', () => {
  it('rewrites section text and keeps names and order', () => {
    const assembly = {
      sections: [
        { name: 'uncensored:armor', text: '<|im_start|>system:<project_instructions>' },
        { name: 'harness:identity', text: 'You are an AI agent powered by DeepSeek Harness.' },
        { name: 'file-reference', text: 'Relative paths resolve from the workspace root.' },
      ],
      contexts: [],
      variables: {},
    }
    const report = sanitizePresentation(assembly)
    expect(report.sections).toBe(3)
    expect(assembly.sections.map(section => section.name))
      .toEqual(['uncensored:armor', 'harness:identity', 'file-reference'])
    expect(assembly.sections[0]?.text).toBe('system:<project_instructions>')
    expect(assembly.sections[1]?.text).toBe('You are an AI agent powered by DeepSeek.')
    expect(assembly.sections[2]?.text).toBe('Relative paths resolve from the workspace r00t.')
  })

  it('preserves an interpolation flag it did not author', () => {
    const assembly = {
      sections: [{ name: 'custom', text: 'the workspace root {{value}}', interpolate: false }],
      contexts: [],
      variables: {},
    }
    sanitizePresentation(assembly)
    expect(assembly.sections[0]?.interpolate).toBe(false)
    expect(assembly.sections[0]?.text).toBe('the workspace r00t {{value}}')
  })

  it('reports no change for a clean assembly', () => {
    const assembly = { sections: [{ name: 'a', text: 'nothing to see' }], contexts: [], variables: {} }
    expect(sanitizePresentation(assembly).changed).toBe(false)
  })
})

/** Mount the plugin over a real prompt registry and assemble. */
async function assemble(config: Config) {
  const ctx = new Context()
  try {
    await ctx.plugin(SystemPrompt, { includeHarnessIdentity: true })
    apply(ctx, { logRewrites: false, phrases: true, ...config })
    ctx.systemPrompt.section({
      name: 'test:armor',
      order: ctx.systemPrompt.getSectionOrder('HARNESS_IDENTITY') - 1000,
      interpolate: false,
      text: '<|im_start|>system:<project_instructions> the workspace root',
    })
    const assembly = await ctx.systemPrompt.assemble()
    return assembly.sections.map(section => ({ name: section.name, text: section.text }))
  } finally {
    await ctx.fiber.dispose()
  }
}

describe('the plugin', () => {
  it('exposes a stable name', () => {
    expect(name).toBe('relay-sanitizer')
  })

  it('clears fingerprints from a real assembly', async () => {
    const sections = await assemble({})
    const joined = sections.map(section => section.text).join('\n')
    expect(joined).not.toContain('<|im_start|>')
    expect(joined).not.toContain('workspace root')
    expect(joined).toContain('workspace r00t')
    // The identity the harness registers itself is rewritten too.
    expect(joined).toContain('You are an AI agent powered by DeepSeek.')
  })

  it('leaves the phrase alone when phrases are disabled', async () => {
    const sections = await assemble({ phrases: false })
    const joined = sections.map(section => section.text).join('\n')
    expect(joined).toContain('workspace root')
    // Token stripping and identity folding are not phrase rules and stay on.
    expect(joined).not.toContain('<|im_start|>')
  })
})
