import { API_BASE_URL } from "../config/env";

export const apiFetch = async (
  endpoint: string,
  options?: RequestInit
): Promise<Response> => {
  const url = `${API_BASE_URL}${endpoint}`;
  return fetch(url, options);
};
