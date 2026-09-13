import { api } from './api';

export const modelService = {
  async getModels() {
    return await api.get('/api/v1/models');
  },
};
