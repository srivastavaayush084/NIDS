import apiClient from './client';

export const usersApi = {
  /**
   * Retrieve paginated list of users (Admin only).
   */
  async listUsers(params = {}) {
    return apiClient.get('/api/v1/users', { params });
  },

  async getUsers(params = {}) {
    return this.listUsers(params);
  },

  /**
   * Create a new user account (Admin only).
   */
  async createUser(userData) {
    return apiClient.post('/api/v1/users', userData);
  },

  /**
   * Retrieve specific user details by ID.
   */
  async getUser(userId) {
    return apiClient.get(`/api/v1/users/${userId}`);
  },

  /**
   * Update user profile, role, or active status (Admin only).
   */
  async updateUser(userId, updateData) {
    return apiClient.patch(`/api/v1/users/${userId}`, updateData);
  },

  /**
   * Deactivate a user account (Admin only).
   */
  async deactivateUser(userId) {
    return apiClient.delete(`/api/v1/users/${userId}`);
  },
};

export default usersApi;
