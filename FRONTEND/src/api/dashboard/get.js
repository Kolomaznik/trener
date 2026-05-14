import { apiClient } from '../client.js';

export async function getDashboard() {
  const response = await apiClient.get('/dashboard');
  return response.data;
}
