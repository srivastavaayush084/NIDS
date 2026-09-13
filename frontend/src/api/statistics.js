import apiClient from './client';

export const statisticsApi = {
  /**
   * Get real-time SOC dashboard summary statistics (KPI counts, severity breakdown).
   */
  async getDashboardSummary(params = {}) {
    return apiClient.get('/api/v1/statistics/summary', { params });
  },

  /**
   * Get detailed alert analytics (severity distributions, top attacker IPs, target IPs).
   */
  async getAlertStatistics(params = {}) {
    return apiClient.get('/api/v1/statistics/alerts', { params });
  },

  /**
   * Get multi-model evaluation and benchmark comparison metrics.
   */
  async getModelStatistics() {
    return apiClient.get('/api/v1/statistics/models');
  },
};

export default statisticsApi;
