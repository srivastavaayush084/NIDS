/**
 * Centralized API Client for AI-Based Zero-Day Attack Detection System.
 * Handles base URL configuration, Bearer token injection, transparent 401 refresh,
 * request timeouts, query string serialization, and error normalization.
 */

const DEFAULT_BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 15000;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL;

const ACCESS_TOKEN_KEY = 'zeroday_access_token';
const REFRESH_TOKEN_KEY = 'zeroday_refresh_token';
const USER_KEY = 'zeroday_user_profile';

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export function formatQueryParams(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.append(key, value);
    }
  });
  const queryString = query.toString();
  return queryString ? `?${queryString}` : '';
}

export class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this._isRefreshing = false;
    this._refreshSubscribers = [];
  }

  // Token storage management
  getAccessToken() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(ACCESS_TOKEN_KEY);
      }
      if (typeof localStorage !== 'undefined') {
        return localStorage.getItem(ACCESS_TOKEN_KEY);
      }
    } catch {
      return null;
    }
    return null;
  }

  getRefreshToken() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(REFRESH_TOKEN_KEY);
      }
      if (typeof localStorage !== 'undefined') {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
      }
    } catch {
      return null;
    }
    return null;
  }

  getUserProfile() {
    try {
      let data = null;
      if (typeof window !== 'undefined' && window.localStorage) {
        data = window.localStorage.getItem(USER_KEY);
      } else if (typeof localStorage !== 'undefined') {
        data = localStorage.getItem(USER_KEY);
      }
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  }

  setSession(accessToken, refreshToken, user) {
    try {
      const storage = typeof window !== 'undefined' && window.localStorage ? window.localStorage : (typeof localStorage !== 'undefined' ? localStorage : null);
      if (storage) {
        if (accessToken) storage.setItem(ACCESS_TOKEN_KEY, accessToken);
        if (refreshToken) storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        if (user) storage.setItem(USER_KEY, JSON.stringify(user));
      }
    } catch {
      // ignore storage errors
    }
  }

  clearSession() {
    try {
      const storage = typeof window !== 'undefined' && window.localStorage ? window.localStorage : (typeof localStorage !== 'undefined' ? localStorage : null);
      if (storage) {
        storage.removeItem(ACCESS_TOKEN_KEY);
        storage.removeItem(REFRESH_TOKEN_KEY);
        storage.removeItem(USER_KEY);
      }
    } catch {
      // ignore
    }
    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
      window.dispatchEvent(new CustomEvent('zeroday:auth:unauthorized'));
    }
  }

  _onRefreshed(newAccessToken) {
    this._refreshSubscribers.forEach((cb) => cb(newAccessToken));
    this._refreshSubscribers = [];
  }

  _addRefreshSubscriber(cb) {
    this._refreshSubscribers.push(cb);
  }

  async request(endpoint, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body,
      params,
      timeout = DEFAULT_TIMEOUT_MS,
      _retry = false,
    } = options;

    const queryString = formatQueryParams(params);
    const url = `${this.baseUrl}${endpoint}${queryString}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    const token = this.getAccessToken();
    const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...authHeaders,
        ...headers,
      },
      signal: controller.signal,
    };

    if (body !== undefined && body !== null) {
      config.body = typeof body === 'string' ? body : JSON.stringify(body);
    }

    try {
      const response = await fetch(url, config);
      clearTimeout(timer);

      // Attempt to parse JSON body
      let data = null;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json().catch(() => null);
      } else {
        const text = await response.text().catch(() => '');
        data = text ? { message: text } : null;
      }

      // Handle 401 Unauthorized & Token Refresh
      if (response.status === 401 && !_retry && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
        const refreshToken = this.getRefreshToken();
        if (refreshToken) {
          if (!this._isRefreshing) {
            this._isRefreshing = true;
            try {
              const refreshRes = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
              });

              if (refreshRes.ok) {
                const refreshData = await refreshRes.json();
                this.setSession(refreshData.access_token, refreshData.refresh_token, refreshData.user);
                this._isRefreshing = false;
                this._onRefreshed(refreshData.access_token);
                // Retry initial request
                return this.request(endpoint, { ...options, _retry: true });
              } else {
                this._isRefreshing = false;
                this.clearSession();
                throw new ApiError('Session expired. Please log in again.', 401);
              }
            } catch (err) {
              this._isRefreshing = false;
              this.clearSession();
              throw new ApiError('Session expired. Please log in again.', 401);
            }
          } else {
            // Queue subsequent calls until refresh completes
            return new Promise((resolve, reject) => {
              this._addRefreshSubscriber((newToken) => {
                this.request(endpoint, { ...options, _retry: true })
                  .then(resolve)
                  .catch(reject);
              });
            });
          }
        } else {
          this.clearSession();
        }
      }

      if (!response.ok) {
        let serverMessage = null;
        if (data) {
          if (data.error && typeof data.error === 'object' && data.error.message) {
            serverMessage = data.error.message;
          } else if (typeof data.error === 'string') {
            serverMessage = data.error;
          } else if (data.detail) {
            serverMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
          } else if (data.message) {
            serverMessage = data.message;
          }
        }

        let message = serverMessage || `Request failed with status ${response.status}`;

        if (response.status === 400) {
          message = `Bad Request: ${message}`;
        } else if (response.status === 401) {
          message = message || 'Unauthorized access.';
        } else if (response.status === 403) {
          message = `Access Denied: ${message}`;
        } else if (response.status === 404) {
          message = `Resource Not Found: ${message}`;
        } else if (response.status === 409) {
          message = `Conflict: ${message}`;
        } else if (response.status === 422) {
          message = `Validation Error: ${message}`;
        } else if (response.status === 429) {
          message = `Rate Limit Exceeded: ${message}`;
        } else if (response.status === 500) {
          message = `Internal Server Error: ${message}`;
        } else if (response.status === 503) {
          message = `Service Unavailable: Backend detection service offline.`;
        }

        throw new ApiError(message, response.status, data);
      }

      return data;
    } catch (error) {
      clearTimeout(timer);

      if (error.name === 'AbortError') {
        throw new ApiError('Request timeout: The server took too long to respond.', 408);
      }
      if (error instanceof ApiError) {
        throw error;
      }

      console.warn(`[Network Error] Failed to connect to ${url}:`, error.message);
      throw new ApiError(
        'Connection unavailable. Ensure backend server is running at ' + this.baseUrl,
        0,
        { originalError: error.message }
      );
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  }

  patch(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
export default apiClient;
