import apiClient from './client';

export const detectionApi = {
  /**
   * List historical detection events with backend pagination & filtering.
   */
  async getDetections(params = {}) {
    return apiClient.get('/api/v1/detection', { params });
  },

  /**
   * Get full detection event details by detection ID.
   */
  async getDetection(detectionId) {
    return apiClient.get(`/api/v1/detection/${detectionId}`);
  },

  /**
   * Run manual detection on a single network flow event.
   */
  async analyzeSingle(payload) {
    return apiClient.post('/api/v1/detection', payload);
  },

  /**
   * Run batch detection on a list of network flow events.
   */
  async analyzeBatch(payload) {
    return apiClient.post('/api/v1/detection/batch', payload);
  },

  /**
   * Run sequence detection (LSTM temporal window).
   */
  async analyzeSequence(payload) {
    return apiClient.post('/api/v1/detection/sequence', payload);
  },
};

export default detectionApi;
