import apiClient from './client';

export const monitoringApi = {
  /**
   * Get real-time monitoring telemetry, throughput rates, and buffer utilization.
   */
  async getStatus() {
    return apiClient.get('/api/v1/monitoring/status');
  },

  /**
   * Start live packet sniffing or streaming PCAP file replay.
   */
  async startMonitoring(payload) {
    return apiClient.post('/api/v1/monitoring/start', payload);
  },

  /**
   * Stop active packet capture session and flush buffers.
   */
  async stopMonitoring() {
    return apiClient.post('/api/v1/monitoring/stop');
  },

  /**
   * Execute an isolated synchronous PCAP file replay benchmark.
   */
  async testPcap(payload) {
    return apiClient.post('/api/v1/monitoring/test-pcap', payload);
  },

  /**
   * Get feature compatibility matrix for all models.
   */
  async getCompatibility(datasetName = 'synthetic') {
    return apiClient.get('/api/v1/monitoring/compatibility', {
      params: { dataset_name: datasetName },
    });
  },

  /**
   * List detected host network capture interfaces.
   */
  async getInterfaces() {
    return apiClient.get('/api/v1/monitoring/interfaces');
  },
};

export default monitoringApi;
