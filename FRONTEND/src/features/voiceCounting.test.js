import { describe, expect, it } from 'vitest';
import {
  computeSessionStats,
  parseNumberFromTokens,
  shouldAcceptEvent,
  tokenizeTranscript,
} from './voiceCounting.js';

describe('voiceCounting utils', () => {
  it('tokenizes and trims transcript', () => {
    expect(tokenizeTranscript('  Ahoj,  5!   tři. ')).toEqual(['ahoj', '5', 'tři']);
  });

  it('parses numeric digits and czech words', () => {
    expect(parseNumberFromTokens(['12'], 0)).toMatchObject({ value: 12, consumed: 1 });
    expect(parseNumberFromTokens(['tři'], 0)).toMatchObject({ value: 3, consumed: 1 });
    expect(parseNumberFromTokens(['dvacet', 'jedna'], 0)).toMatchObject({ value: 21, consumed: 2 });
  });

  it('returns null for invalid token', () => {
    expect(parseNumberFromTokens(['ahoj'], 0)).toBeNull();
    expect(parseNumberFromTokens([], 0)).toBeNull();
  });

  it('deduplicates same token in short window', () => {
    const prev = { value: 5, token: 'pet', timestampMs: 1000 };
    const withinWindow = { value: 5, token: 'pet', timestampMs: 1500 };
    const afterWindow = { value: 5, token: 'pet', timestampMs: 2401 };

    expect(shouldAcceptEvent(withinWindow, prev, 1200)).toBe(false);
    expect(shouldAcceptEvent(afterWindow, prev, 1200)).toBe(true);
  });

  it('computes stats including frequency and intervals', () => {
    const events = [
      { value: 3, timestampMs: 1000 },
      { value: 3, timestampMs: 1800 },
      { value: 8, timestampMs: 2600 },
    ];
    expect(computeSessionStats(events)).toEqual({
      count: 3,
      min: 3,
      max: 8,
      average: 4.67,
      frequency: { 3: 2, 8: 1 },
      intervalsMs: [800, 800],
    });
    expect(computeSessionStats([])).toEqual({
      count: 0,
      min: null,
      max: null,
      average: null,
      frequency: {},
      intervalsMs: [],
    });
  });
});
