import { describe, it, expect } from 'vitest';
import {
  parseDate,
  formatDate,
  formatRelativeTime,
  formatBytes,
  formatNumber,
  formatDuration,
  formatPercentage,
} from '../utils/formatters';

describe('formatters utility suite', () => {
  it('parses dates with timezone awareness', () => {
    expect(parseDate(null)).toBeNull();
    expect(parseDate('')).toBeNull();
    expect(parseDate('invalid-date')).toBeNull();

    // Naive ISO string without Z should be parsed as UTC
    const naiveIso = '2026-09-13T10:00:00';
    const parsedNaive = parseDate(naiveIso);
    expect(parsedNaive).not.toBeNull();
    expect(parsedNaive.toISOString()).toBe('2026-09-13T10:00:00.000Z');

    // ISO string with space separator
    const spaceIso = '2026-09-13 10:00:00';
    const parsedSpace = parseDate(spaceIso);
    expect(parsedSpace).not.toBeNull();
    expect(parsedSpace.toISOString()).toBe('2026-09-13T10:00:00.000Z');

    // Standard UTC ISO string with Z
    const utcIso = '2026-09-13T10:00:00Z';
    const parsedUtc = parseDate(utcIso);
    expect(parsedUtc.toISOString()).toBe('2026-09-13T10:00:00.000Z');
  });

  it('formats dates properly', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('invalid-date')).toBe('invalid-date');
    const valid = formatDate('2026-09-08T12:00:00Z');
    expect(valid).toBeDefined();
    expect(typeof valid).toBe('string');
  });

  it('formats relative times and handles timezone offsets accurately', () => {
    expect(formatRelativeTime(null)).toBe('—');
    const now = new Date();
    expect(formatRelativeTime(now.toISOString())).toBe('just now');

    // 2 minutes ago, formatted as naive ISO string without 'Z'
    const twoMinAgo = new Date(now.getTime() - 2 * 60 * 1000);
    const naiveTwoMinAgoIso = twoMinAgo.toISOString().replace('Z', '');
    // Should correctly resolve to '2m ago' and NOT '5h ago'
    expect(formatRelativeTime(naiveTwoMinAgoIso)).toBe('2m ago');

    // Clock skew tolerance (1-2 seconds in future returns 'just now')
    const slightlyFuture = new Date(now.getTime() + 2000);
    expect(formatRelativeTime(slightlyFuture.toISOString())).toBe('just now');
  });

  it('formats byte volumes accurately', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1048576)).toBe('1 MB');
    expect(formatBytes(1073741824)).toBe('1 GB');
  });

  it('formats integer and floating point numbers with commas', () => {
    expect(formatNumber(0)).toBe('0');
    expect(formatNumber(1234567)).toBe('1,234,567');
  });

  it('formats second durations into readable text', () => {
    expect(formatDuration(0.5)).toBe('0.5s');
    expect(formatDuration(45)).toBe('45.0s');
    expect(formatDuration(125)).toBe('2m 5s');
    expect(formatDuration(3665)).toBe('1h 1m');
  });

  it('formats percentage values with decimal control', () => {
    expect(formatPercentage(98.245, 1)).toBe('98.2%');
    expect(formatPercentage(100, 0)).toBe('100%');
  });
});
