import { apiClient } from '../client.js';

export async function getUserExercises() {
  const response = await apiClient.get('/user-exercises');
  return response.data;
}
