import { apiClient } from '../client.js';

export async function postWorkoutSession(data) {
  const response = await apiClient.post('/workout-sessions', data);
  return response.data;
}
