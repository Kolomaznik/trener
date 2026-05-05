import { apiClient } from '../client.js';

export async function getExerciseDetail(exerciseId) {
  const response = await apiClient.get(`/exercises/${exerciseId}`);
  return response.data;
}
