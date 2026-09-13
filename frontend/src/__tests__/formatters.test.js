import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatRelativeTime,
  formatBytes,
  formatNumber,
  formatDuration,
  formatPercentage,
} from '../utils/formatters';

describe('formatters utility suite', () => {
  it('formats dates properly', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('invalid-date')).toBe('invalid-date');
    const valid = formatDate('2026-09-08T12:00:00Z');
    expect(valid).toBeDefined();
    expect(typeof valid).toBe('string');
  });

  it('formats relative times', () => {
    expect(formatRelativeTime(null)).toBe('—');
    const now = new Date();
    expect(formatRelativeTime(now.toISOString())).toBe('just now');
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
