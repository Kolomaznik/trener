import { apiClient } from '../client.js';

export async function putExerciseSeries(data) {
  const response = await apiClient.put('/exercises/series', data);
  return response.data;
}
