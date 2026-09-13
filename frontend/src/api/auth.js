import apiClient from './client';

export const authApi = {
  /**
   * Authenticate with username or email + password.
   */
  async login(credentials) {
    return apiClient.post('/api/v1/auth/login', credentials);
  },

  /**
   * Refresh access token using active refresh token.
   */
  async refresh(refreshToken) {
    return apiClient.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
  },

  async refreshToken(token) {
    return this.refresh(token);
  },

  /**
   * Terminate active user session.
   */
  async logout() {
    return apiClient.post('/api/v1/auth/logout', {});
  },

  /**
   * Retrieve current authenticated user profile.
   */
  async getCurrentUser() {
    return apiClient.get('/api/v1/auth/me');
  },
};

export default authApi;
