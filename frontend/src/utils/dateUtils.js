/**
 * Date utility functions for proper timezone handling
 *
 * Key principles:
 * 1. Backend stores ALL dates as UTC
 * 2. Frontend works in local timezone for display
 * 3. When sending to backend: convert local → UTC via toISOString()
 * 4. When receiving from backend: dates are UTC, convert to local for display
 */

/**
 * Get the system timezone offset in hours
 * @returns {number} Offset in hours (e.g., -5 for EST, +1 for CET)
 */
export function getTimezoneOffsetHours() {
  const offsetMinutes = new Date().getTimezoneOffset();
  return -offsetMinutes / 60; // Negative because getTimezoneOffset returns opposite sign
}

/**
 * Log date information for debugging
 * @param {string} label - Label for the log
 * @param {Date|string} date - Date to log
 */
export function logDateInfo(label, date) {
  const d = date instanceof Date ? date : new Date(date);

  console.group(`📅 ${label}`);
  console.log('toString():', d.toString());
  console.log('toISOString():', d.toISOString());
  console.log('toLocaleString():', d.toLocaleString());
  console.log('getTime():', d.getTime());

  const offsetHours = getTimezoneOffsetHours();
  const utcDate = new Date(d.toISOString());
  const hourDiff = d.getHours() - utcDate.getHours();

  console.log('Local hours:', d.getHours());
  console.log('UTC hours:', utcDate.getHours());
  console.log('Timezone offset (hours):', offsetHours);
  console.log('Hour difference:', hourDiff);
  console.log('Matches timezone offset?', Math.abs(hourDiff) === Math.abs(offsetHours) || hourDiff === 0);
  console.groupEnd();
}

/**
 * Convert a UTC ISO string to a Date object in local timezone
 * The resulting Date object will have the correct local time
 *
 * @param {string} utcIsoString - UTC ISO string from backend (e.g., "2025-11-15T16:00:00Z")
 * @returns {Date} Date object representing the same instant in local timezone
 */
export function utcToLocal(utcIsoString) {
  return new Date(utcIsoString);
}

/**
 * Create a Date object from local time components
 * This ensures we're creating a date in the LOCAL timezone
 *
 * @param {number} year
 * @param {number} month - 0-11 (January = 0)
 * @param {number} date - 1-31
 * @param {number} hours - 0-23
 * @param {number} minutes - 0-59
 * @param {number} seconds - 0-59 (optional)
 * @returns {Date} Date object in local timezone
 */
export function createLocalDate(year, month, date, hours = 0, minutes = 0, seconds = 0) {
  return new Date(year, month, date, hours, minutes, seconds, 0);
}

/**
 * Convert a Date object to ISO string (UTC)
 * This is what we send to the backend
 *
 * @param {Date} localDate - Date in local timezone
 * @returns {string} ISO string in UTC
 */
export function localToUtcIso(localDate) {
  return localDate.toISOString();
}

/**
 * Format a datetime for datetime-local input
 * The datetime-local input expects: "YYYY-MM-DDTHH:MM"
 *
 * @param {string|Date} dateInput - UTC ISO string or Date object
 * @returns {string} Formatted string for datetime-local input
 */
export function formatForDateTimeLocal(dateInput) {
  const date = dateInput instanceof Date ? dateInput : new Date(dateInput);

  // Get local time components
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Parse a datetime-local input value to UTC ISO string
 * The input format is: "YYYY-MM-DDTHH:MM" in LOCAL timezone
 * We need to convert this to UTC ISO string for the backend
 *
 * @param {string} dateTimeLocalString - Value from datetime-local input
 * @returns {string} UTC ISO string
 */
export function parseDateTimeLocal(dateTimeLocalString) {
  // The datetime-local value is in local timezone
  // new Date() constructor will parse it as local time
  const localDate = new Date(dateTimeLocalString);

  // Convert to UTC ISO string
  return localDate.toISOString();
}

/**
 * Compare two date/time values for debugging
 * @param {string|Date} date1
 * @param {string|Date} date2
 * @returns {Object} Comparison results
 */
export function compareDates(date1, date2) {
  const d1 = date1 instanceof Date ? date1 : new Date(date1);
  const d2 = date2 instanceof Date ? date2 : new Date(date2);

  const diffMs = d1.getTime() - d2.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  return {
    date1Iso: d1.toISOString(),
    date2Iso: d2.toISOString(),
    differenceMs: diffMs,
    differenceHours: diffHours,
    areEqual: diffMs === 0,
  };
}

/**
 * Create a diagnostic table for date conversions
 * @param {string} operation - Description of the operation
 * @param {any} input - Input value
 * @param {string} storedUtc - What was stored in DB (UTC)
 * @param {string} returnedUtc - What was returned from DB (UTC)
 * @param {string} displayedLocal - What is displayed to user (local)
 */
export function createDateDiagnosticTable(operation, input, storedUtc, returnedUtc, displayedLocal) {
  console.table({
    Operation: operation,
    'Input (from UI)': input,
    'Stored (UTC in DB)': storedUtc,
    'Returned (UTC from DB)': returnedUtc,
    'Displayed (Local in UI)': displayedLocal,
  });
}
