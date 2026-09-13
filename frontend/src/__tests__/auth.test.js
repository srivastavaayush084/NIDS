import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClient, ApiError } from '../api/client';
import { authApi } from '../api/auth';
import { usersApi } from '../api/users';

describe('Frontend Authentication and RBAC API Suite', () => {
  const originalFetch = global.fetch;
  const originalLocalStorage = global.localStorage;

  let mockStorage = {};

  beforeEach(() => {
    mockStorage = {};
    global.localStorage = {
      getItem: vi.fn((key) => mockStorage[key] || null),
      setItem: vi.fn((key, value) => {
        mockStorage[key] = String(value);
      }),
      removeItem: vi.fn((key) => {
        delete mockStorage[key];
      }),
      clear: vi.fn(() => {
        mockStorage = {};
      }),
    };
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.localStorage = originalLocalStorage;
  });

  it('injects Bearer authorization token into outgoing requests', async () => {
    mockStorage['zeroday_access_token'] = 'jwt.mock.access.token';
    const client = new ApiClient('http://localhost:8000');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({ status: 'healthy' }),
    });

    await client.get('/api/v1/statistics/summary');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/statistics/summary',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer jwt.mock.access.token',
        }),
      })
    );
  });

  it('performs user login and parses tokens and roles', async () => {
    const mockAuthResponse = {
      access_token: 'mock-access-token-123',
      refresh_token: 'mock-refresh-token-456',
      token_type: 'bearer',
      user: {
        user_id: 'usr-admin-01',
        username: 'admin',
        email: 'admin@zeroday.ai',
        role: 'admin',
        is_active: true,
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => mockAuthResponse,
    });

    const res = await authApi.login('admin', 'AdminPass123!');
    expect(res.access_token).toBe('mock-access-token-123');
    expect(res.user.role).toBe('admin');
    expect(res.user.username).toBe('admin');
  });

  it('performs token refresh correctly', async () => {
    const mockRefreshResponse = {
      access_token: 'new-access-token-789',
      refresh_token: 'mock-refresh-token-456',
      token_type: 'bearer',
      user: {
        user_id: 'usr-admin-01',
        username: 'admin',
        role: 'admin',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => mockRefreshResponse,
    });

    const res = await authApi.refreshToken('mock-refresh-token-456');
    expect(res.access_token).toBe('new-access-token-789');
    expect(res.user.username).toBe('admin');
  });

  it('calls admin users API endpoints with proper payloads', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({
        users: [
          { user_id: 'usr-1', username: 'analyst_bob', role: 'analyst', is_active: true },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      }),
    });

    const res = await usersApi.getUsers({ page: 1, role: 'analyst' });
    expect(res.total).toBe(1);
    expect(res.users[0].username).toBe('analyst_bob');
  });

  it('handles user creation via admin API', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      headers: { get: () => 'application/json' },
      json: async () => ({
        message: 'User account provisioned successfully',
        user: {
          user_id: 'usr-created-99',
          username: 'new_analyst',
          email: 'analyst@test.local',
          role: 'analyst',
          is_active: true,
        },
      }),
    });

    const res = await usersApi.createUser({
      username: 'new_analyst',
      email: 'analyst@test.local',
      password: 'SecurePassword123!',
      role: 'analyst',
      full_name: 'New Analyst',
    });

    expect(res.user.username).toBe('new_analyst');
    expect(res.user.role).toBe('analyst');
  });

  it('handles user deactivation via admin API', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({
        message: 'User account usr-deact-01 deactivated successfully',
        user_id: 'usr-deact-01',
        is_active: false,
      }),
    });

    const res = await usersApi.deactivateUser('usr-deact-01');
    expect(res.is_active).toBe(false);
  });

  it('maps HTTP status codes to user-safe error messages in User Management', async () => {
    const { getUserSafeErrorMessage } = await import('../pages/Users');

    expect(getUserSafeErrorMessage({ status: 401 })).toBe('Your session has expired. Please log in again.');
    expect(getUserSafeErrorMessage({ status: 403 })).toBe('You do not have permission to manage users.');
    expect(getUserSafeErrorMessage({ status: 404 })).toBe('User management service is unavailable.');
    expect(getUserSafeErrorMessage({ status: 500 })).toBe('User management service encountered an internal error.');
    expect(getUserSafeErrorMessage({ status: 0 })).toBe('Unable to communicate with the backend service.');
    expect(getUserSafeErrorMessage(new Error('Failed to fetch'))).toBe('Unable to communicate with the backend service.');
    expect(getUserSafeErrorMessage({ message: 'Custom validation error' })).toBe('Custom validation error');
  });
});
