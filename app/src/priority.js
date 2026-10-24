/**
 * Calculates the incident priority for PhoenixCI incident management.
 * 
 * Rules:
 * - 'P1': severity === 'critical' OR affectedUsers >= 1000 OR (isProduction && affectedUsers >= 100)
 * - 'P2': severity === 'high' OR affectedUsers >= 500
 * - 'P3': severity === 'medium' OR affectedUsers >= 50
 * - 'P4': all other valid cases
 * 
 * @param {string} severity - 'critical', 'high', 'medium', or 'low'
 * @param {number} affectedUsers - non-negative integer
 * @param {boolean} isProduction - true if affecting production environment
 * @returns {string} Priority code ('P1', 'P2', 'P3', 'P4')
 */
function calculateIncidentPriority(severity, affectedUsers, isProduction = false) {
  if (typeof severity !== 'string') {
    throw new TypeError('severity must be a string');
  }

  const normalizedSeverity = severity.trim().toLowerCase();
  const validSeverities = ['critical', 'high', 'medium', 'low'];
  if (!validSeverities.includes(normalizedSeverity)) {
    throw new Error(`Invalid severity: ${severity}`);
  }

  if (typeof affectedUsers !== 'number' || isNaN(affectedUsers) || affectedUsers < 0) {
    throw new TypeError('affectedUsers must be a non-negative number');
  }

  if (normalizedSeverity === 'critical' || affectedUsers >= 1000 || (isProduction && affectedUsers >= 100)) {
    return 'P1';
  }

  if (normalizedSeverity === 'high' || affectedUsers >= 500) {
    return 'P2';
  }

  if (normalizedSeverity === 'medium' || affectedUsers >= 50) {
    return 'P3';
  }

  return 'P4';
}

module.exports = {
  calculateIncidentPriority
};
