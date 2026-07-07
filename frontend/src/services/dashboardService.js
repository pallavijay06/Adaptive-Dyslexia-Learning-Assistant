import api from '../config/api';

export const dashboardService = {
  getDashboard: async (userId) => {
    const response = await api.get(`/dashboard/${userId}`);
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Unable to load dashboard data.');
    }

    return response.data.dashboard ?? {};
  },
};
