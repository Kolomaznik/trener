import { apiClient } from '../../client.js';

export async function getUserSettings() {
  const response = await apiClient.get('/user');
  return response.data;
}
