const ONES = {
  nula: 0,
  nic: 0,
  jeden: 1,
  jedna: 1,
  jedno: 1,
  dva: 2,
  dve: 2,
  tři: 3,
  tri: 3,
  čtyři: 4,
  ctyri: 4,
  pět: 5,
  pet: 5,
  šest: 6,
  sest: 6,
  sedm: 7,
  osm: 8,
  devět: 9,
  devet: 9,
};

const TEENS = {
  deset: 10,
  jedenáct: 11,
  jedenact: 11,
  dvanáct: 12,
  dvanact: 12,
  třináct: 13,
  trinact: 13,
  čtrnáct: 14,
  ctrnact: 14,
  patnáct: 15,
  patnact: 15,
  šestnáct: 16,
  sestnact: 16,
  sedmnáct: 17,
  sedmnact: 17,
  osmnáct: 18,
  osmnact: 18,
  devatenáct: 19,
  devatenact: 19,
};

const TENS = {
  dvacet: 20,
  třicet: 30,
  tricet: 30,
  čtyřicet: 40,
  ctyricet: 40,
  padesát: 50,
  padesat: 50,
  šedesát: 60,
  sedesat: 60,
  sedmdesát: 70,
  sedmdesat: 70,
  osmdesát: 80,
  osmdesat: 80,
  devadesát: 90,
  devadesat: 90,
};

const NON_WORD_EDGE = /^[^\p{L}\p{N}-]+|[^\p{L}\p{N}-]+$/gu;

export function tokenizeTranscript(transcript) {
  if (!transcript) return [];

  return transcript
    .split(/\s+/)
    .map((token) => token.toLowerCase().replace(NON_WORD_EDGE, '').trim())
    .filter(Boolean);
}

export function parseNumberFromTokens(tokens, index) {
  const token = tokens[index];
  if (!token) return null;

  if (/^-?\d+$/.test(token)) {
    return { value: Number.parseInt(token, 10), consumed: 1, token };
  }

  if (Object.hasOwn(TEENS, token)) {
    return { value: TEENS[token], consumed: 1, token };
  }

  if (Object.hasOwn(TENS, token)) {
    const nextToken = tokens[index + 1];
    if (nextToken && Object.hasOwn(ONES, nextToken) && ONES[nextToken] > 0) {
      return {
        value: TENS[token] + ONES[nextToken],
        consumed: 2,
        token: `${token} ${nextToken}`,
      };
    }
    return { value: TENS[token], consumed: 1, token };
  }

  if (Object.hasOwn(ONES, token)) {
    return { value: ONES[token], consumed: 1, token };
  }

  return null;
}

export function shouldAcceptEvent(nextEvent, previousEvent, dedupWindowMs = 1200) {
  if (!previousEvent) return true;

  const withinWindow = nextEvent.timestampMs - previousEvent.timestampMs <= dedupWindowMs;
  const sameValue = nextEvent.value === previousEvent.value;
  const sameToken = nextEvent.token === previousEvent.token;

  return !(withinWindow && sameValue && sameToken);
}

export function computeSessionStats(events) {
  const values = events.map((event) => event.value);

  if (values.length === 0) {
    return {
      count: 0,
      min: null,
      max: null,
      average: null,
      frequency: {},
      intervalsMs: [],
    };
  }

  const sum = values.reduce((acc, value) => acc + value, 0);
  const frequency = events.reduce((acc, event) => {
    const key = String(event.value);
    return { ...acc, [key]: (acc[key] ?? 0) + 1 };
  }, {});
  const intervalsMs = events.slice(1).map((event, idx) => event.timestampMs - events[idx].timestampMs);

  return {
    count: values.length,
    min: Math.min(...values),
    max: Math.max(...values),
    average: Number((sum / values.length).toFixed(2)),
    frequency,
    intervalsMs,
  };
}
