import { api } from './api';

export const healthService = {
  async getHealth() {
    return await api.get('/api/health');
  },
};
