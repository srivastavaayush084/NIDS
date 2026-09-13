import apiClient from './client';

export const alertsApi = {
  /**
   * List security alerts with backend filtering, pagination, and sorting.
   */
  async getAlerts(params = {}) {
    return apiClient.get('/api/v1/alerts', { params });
  },

  /**
   * Get single security alert details by ID.
   */
  async getAlert(alertId) {
    return apiClient.get(`/api/v1/alerts/${alertId}`);
  },

  /**
   * Transition alert state to ACKNOWLEDGED.
   */
  async acknowledgeAlert(alertId, userId = 'soc_analyst') {
    return apiClient.patch(`/api/v1/alerts/${alertId}/acknowledge`, { user_id: userId });
  },

  /**
   * Transition alert state to RESOLVED with remediation note.
   */
  async resolveAlert(alertId, resolutionNote, userId = 'soc_analyst') {
    return apiClient.patch(`/api/v1/alerts/${alertId}/resolve`, {
      resolution_note: resolutionNote,
      user_id: userId,
    });
  },

  /**
   * Transition alert state to DISMISSED with dismissal reason.
   */
  async dismissAlert(alertId, dismissalReason, userId = 'soc_analyst') {
    return apiClient.patch(`/api/v1/alerts/${alertId}/dismiss`, {
      dismissal_reason: dismissalReason,
      user_id: userId,
    });
  },
};

export default alertsApi;
