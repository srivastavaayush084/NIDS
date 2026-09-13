/**
 * Standardized data formatters for UI presentation.
 */

/**
 * Safely parse a date input (Date instance, timestamp number, or ISO string).
 * If an ISO string lacks timezone information (e.g. "2026-09-13T05:06:57.997000"),
 * standard JavaScript new Date(...) parses it in local client time instead of UTC.
 * Since backend timestamps are recorded in UTC, normalize naive ISO strings to UTC by appending 'Z'.
 */
export function parseDate(dateInput) {
  if (!dateInput) return null;
  if (dateInput instanceof Date) {
    return isNaN(dateInput.getTime()) ? null : dateInput;
  }
  if (typeof dateInput === 'number') {
    const d = new Date(dateInput);
    return isNaN(d.getTime()) ? null : d;
  }
  if (typeof dateInput === 'string') {
    const str = dateInput.trim();
    if (!str) return null;

    // Matches YYYY-MM-DDTHH:mm:ss(.sss) or YYYY-MM-DD HH:mm:ss(.sss) without Z or +/-offset
    const isoWithoutTzRegex = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;
    if (isoWithoutTzRegex.test(str)) {
      const normalized = str.replace(' ', 'T') + 'Z';
      const d = new Date(normalized);
      if (!isNaN(d.getTime())) return d;
    }

    const d = new Date(str);
    return isNaN(d.getTime()) ? null : d;
  }
  return null;
}

export function formatDate(dateInput) {
  if (!dateInput) return '—';
  try {
    const d = parseDate(dateInput);
    if (!d) return String(dateInput);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(d);
  } catch {
    return String(dateInput);
  }
}

export function formatRelativeTime(dateInput) {
  if (!dateInput) return '—';
  try {
    const d = parseDate(dateInput);
    if (!d) return '—';
    const now = new Date();
    // Clamp to 0 to gracefully handle minor clock skew between client and server
    const diffSec = Math.max(0, Math.floor((now.getTime() - d.getTime()) / 1000));

    if (diffSec < 5) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return '—';
  }
}

export function formatBytes(bytes, decimals = 1) {
  if (bytes === 0 || bytes === '0') return '0 B';
  if (!bytes || isNaN(bytes)) return '—';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(Number(bytes)) / Math.log(k));
  if (i < 0) return `${bytes} B`;
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i] || 'B'}`;
}

export function formatNumber(num) {
  if (num === null || num === undefined || isNaN(num)) return '0';
  return new Intl.NumberFormat('en-US').format(num);
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return '0.0s';
  const sec = Number(seconds);
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const mins = Math.floor(sec / 60);
  const remSec = Math.floor(sec % 60);
  if (mins < 60) return `${mins}m ${remSec}s`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hours}h ${remMins}m`;
}

export function formatPercentage(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '0.0%';
  return `${Number(val).toFixed(decimals)}%`;
}
