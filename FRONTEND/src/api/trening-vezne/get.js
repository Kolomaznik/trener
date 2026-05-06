import { apiClient } from '../client.js';

export async function getTreningVezne() {
  const response = await apiClient.get('/trening-vezne');
  return response.data;
}
