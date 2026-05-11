import { apiClient } from '../client.js';

export async function getDashboardMuscleLoad(range = 'week') {
  const response = await apiClient.get('/dashboard/muscle-load', {
    params: { range },
  });
  return response.data;
}
