import { API_BASE_URL } from "../config/env";

export const apiFetch = async (
  endpoint: string,
  options?: RequestInit
): Promise<Response> => {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log("apiFetch URL:", url);
  return fetch(url, options);
};
