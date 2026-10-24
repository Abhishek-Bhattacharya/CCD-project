import { describe, it, expect } from 'vitest';
import { CATEGORIES, CAMPUS_LOCATIONS } from '../lib/constants';

describe('Foundly Constants', () => {
  it('should contain expected default categories', () => {
    expect(CATEGORIES).toContain('Electronics & Tech');
    expect(CATEGORIES).toContain('Keys & Tokens');
    expect(CATEGORIES.length).toBeGreaterThanOrEqual(5);
  });

  it('should contain the requested report locations', () => {
    expect(CAMPUS_LOCATIONS).toEqual([
      'AB-1',
      'AB-2',
      'AB-3',
      'AB-4',
      'AB-5',
      'Gate 1',
      'Gate 2',
      'Gate 3',
      'Gate 4',
      'Gate 5',
      'MAHE-Central Library',
      'Marena',
      'HB-4 NW',
      'HB-4 SW',
      'HB-5',
      'HB-1',
      'HB-2',
      'HB-3',
      'Campus Mart',
      'Other',
    ]);
  });
});