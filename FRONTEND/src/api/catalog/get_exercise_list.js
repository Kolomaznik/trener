import { apiClient } from '../client.js';

export async function getExerciseList() {
  const response = await apiClient.get('/catalog');
  return response.data;
}
