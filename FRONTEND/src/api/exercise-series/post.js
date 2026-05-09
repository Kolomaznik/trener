import { apiClient } from '../client.js';

export async function postExerciseSeries(data) {
  const response = await apiClient.post('/exercise-series', data);
  return response.data;
}
