import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClient, ApiError, formatQueryParams } from '../api/client';

describe('ApiClient and Query Formatter Suite', () => {
  it('serializes query parameters correctly', () => {
    const params = {
      severity: 'CRITICAL',
      page: 1,
      empty: '',
      nullVal: null,
      undefVal: undefined,
    };
    const qs = formatQueryParams(params);
    expect(qs).toBe('?severity=CRITICAL&page=1');
    expect(formatQueryParams({})).toBe('');
  });

  it('normalizes error responses with status codes', async () => {
    const client = new ApiClient('http://localhost:8000');

    // Mock global fetch to return 404
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: 'Security alert not found' }),
    });

    await expect(client.get('/api/v1/alerts/nonexistent')).rejects.toThrow(
      'Resource Not Found: Security alert not found'
    );

    // Mock global fetch to return 503
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      headers: { get: () => 'application/json' },
      json: async () => ({}),
    });

    await expect(client.get('/api/v1/health')).rejects.toThrow(
      'Service Unavailable: Backend detection service offline.'
    );

    // Restore fetch
    global.fetch = originalFetch;
  });

  it('handles network connection failures gracefully', async () => {
    const client = new ApiClient('http://localhost:8000');
    const originalFetch = global.fetch;

    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    await expect(client.get('/api/v1/statistics/summary')).rejects.toThrow(
      'Connection unavailable. Ensure backend server is running'
    );

    global.fetch = originalFetch;
  });
});
