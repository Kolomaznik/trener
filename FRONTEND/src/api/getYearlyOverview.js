import { apiClient } from './client';

export async function getYearlyOverview(endDate) {
  const response = await apiClient.get('/dashboard/yearly-overview', {
    params: endDate ? { end_date: endDate } : undefined,
  });
  return response.data;
}
