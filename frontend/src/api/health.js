import apiClient from './client';

export const healthApi = {
  /**
   * Get basic health status of the API and its subsystems.
   */
  async getHealth() {
    return apiClient.get('/api/v1/health/');
  },

  /**
   * Get detailed diagnostic health telemetry.
   */
  async getDetailedHealth() {
    return apiClient.get('/api/v1/health');
  },
};

export default healthApi;
