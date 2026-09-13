import apiClient from './client';

export const modelsApi = {
  /**
   * List all active registered ML models and metadata.
   */
  async getModels(dataset = 'synthetic') {
    return apiClient.get('/api/v1/models', { params: { dataset } });
  },

  /**
   * Get single model metadata and hyperparameters by name.
   */
  async getModel(modelName, dataset = 'synthetic') {
    return apiClient.get(`/api/v1/models/${modelName}`, { params: { dataset } });
  },

  /**
   * Get multi-model evaluation comparison matrix.
   */
  async getModelComparison(dataset = 'synthetic') {
    return apiClient.get('/api/v1/models/comparison', { params: { dataset } });
  },
};

export default modelsApi;
