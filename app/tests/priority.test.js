const { calculateIncidentPriority } = require('../src/priority');

describe('calculateIncidentPriority', () => {
  test('returns P1 for critical severity regardless of user count', () => {
    expect(calculateIncidentPriority('critical', 0)).toBe('P1');
    expect(calculateIncidentPriority('critical', 5)).toBe('P1');
    expect(calculateIncidentPriority('CRITICAL', 10)).toBe('P1');
  });

  test('returns P1 for >= 1000 affected users regardless of severity', () => {
    expect(calculateIncidentPriority('low', 1000)).toBe('P1');
    expect(calculateIncidentPriority('medium', 5000)).toBe('P1');
  });

  test('returns P1 for production incidents affecting >= 100 users', () => {
    expect(calculateIncidentPriority('low', 100, true)).toBe('P1');
    expect(calculateIncidentPriority('medium', 150, true)).toBe('P1');
  });

  test('returns P2 for high severity or >= 500 users', () => {
    expect(calculateIncidentPriority('high', 10)).toBe('P2');
    expect(calculateIncidentPriority('low', 500)).toBe('P2');
    expect(calculateIncidentPriority('medium', 750)).toBe('P2');
  });

  test('returns P3 for medium severity or >= 50 users', () => {
    expect(calculateIncidentPriority('medium', 10)).toBe('P3');
    expect(calculateIncidentPriority('low', 50)).toBe('P3');
    expect(calculateIncidentPriority('low', 99)).toBe('P3');
  });

  test('returns P4 for low severity with few users', () => {
    expect(calculateIncidentPriority('low', 5)).toBe('P4');
    expect(calculateIncidentPriority('low', 0)).toBe('P4');
  });

  test('throws TypeError on invalid severity type', () => {
    expect(() => calculateIncidentPriority(null, 10)).toThrow(TypeError);
    expect(() => calculateIncidentPriority(123, 10)).toThrow(TypeError);
  });

  test('throws Error on unknown severity value', () => {
    expect(() => calculateIncidentPriority('emergency', 10)).toThrow(/Invalid severity/);
  });

  test('throws TypeError on invalid affectedUsers', () => {
    expect(() => calculateIncidentPriority('low', -1)).toThrow(TypeError);
    expect(() => calculateIncidentPriority('low', 'many')).toThrow(TypeError);
    expect(() => calculateIncidentPriority('low', NaN)).toThrow(TypeError);
  });
});
