import { apiClient } from './client';

export async function getMonthlyOverview(month) {
  const response = await apiClient.get('/dashboard/monthly-overview', {
    params: month ? { month } : undefined,
  });
  return response.data;
}
