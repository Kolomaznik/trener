import { apiClient } from '../client.js';

export async function getDashboard(endDate) {
  const response = await apiClient.get('/dashboard', {
    params: endDate ? { end_date: endDate } : undefined,
  });
  return response.data;
}
