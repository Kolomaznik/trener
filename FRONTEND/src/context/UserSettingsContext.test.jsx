import { describe, expect, it } from 'vitest';
import { isProfileComplete } from './UserSettingsContext.jsx';

describe('isProfileComplete', () => {
  const complete = {
    email: 'a@b.cz',
    gender: 'male',
    height_cm: 180,
    weight_kg: 75,
    birth_year: 1990,
  };

  it('returns true when all required fields are set', () => {
    expect(isProfileComplete(complete)).toBe(true);
  });

  it('returns false for null/undefined input', () => {
    expect(isProfileComplete(null)).toBe(false);
    expect(isProfileComplete(undefined)).toBe(false);
  });

  it.each(['gender', 'height_cm', 'weight_kg', 'birth_year'])(
    'returns false when %s is missing',
    (field) => {
      const partial = { ...complete, [field]: null };
      expect(isProfileComplete(partial)).toBe(false);
    },
  );

  it('returns false when a field is undefined (not just null)', () => {
    const partial = { ...complete };
    delete partial.gender;
    expect(isProfileComplete(partial)).toBe(false);
  });
});
