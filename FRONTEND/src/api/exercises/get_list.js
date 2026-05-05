import { apiClient } from '../client.js';

export async function getExercises({ limit = 100, skip = 0 } = {}) {
  const response = await apiClient.get('/exercises', { params: { limit, skip } });
  return response.data;
}
