import { apiClient } from '../client.js';

export async function getExercisesCatalog() {
  const response = await apiClient.get('/exercises/catalog');
  return response.data;
}
