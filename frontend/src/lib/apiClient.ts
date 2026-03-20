import { API_BASE_URL } from "../config/env";
import { useAppStore } from "../stores/useAppStore";

export class ApiError extends Error {
  status: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: any;

  constructor(
    status: number,
    message: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data?: any
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface ApiClientOptions extends RequestInit {
  timeoutMs?: number;
  skipGlobalError?: boolean;
}

class ApiClient {
  public async fetch(endpoint: string | RequestInfo, options: ApiClientOptions = {}): Promise<Response> {
    const { timeoutMs = 30000, skipGlobalError = false, ...fetchOptions } = options;
    
    let url: string;
    if (typeof endpoint === "string") {
      url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
    } else {
      url = (endpoint as Request).url;
    }

    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: options.signal || controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
      });

      clearTimeout(id);

      if (!response.ok) {
        const clone = response.clone();
        let errorData;
        try {
          errorData = await clone.json();
        } catch {
          errorData = { message: response.statusText };
        }
        
        throw new ApiError(
          response.status, 
          errorData?.detail || errorData?.message || response.statusText, 
          errorData
        );
      }

      return response;
    } catch (error: unknown) {
      clearTimeout(id);
      
      let errorMessage = "Wystąpił nieoczekiwany błąd sieci.";
      
      if (error instanceof Error) {
        errorMessage = error.name === "AbortError" 
          ? "Przekroczono czas oczekiwania na odpowiedź serwera (Timeout)." 
          : error.message;
      }

      if (!skipGlobalError) {
        useAppStore.getState().setGlobalError(errorMessage);
      }
      
      throw error;
    }
  }

  public async request<T>(endpoint: string, options: ApiClientOptions = {}): Promise<T> {
    const response = await this.fetch(endpoint, options);
    
    if (response.status === 204) {
      return {} as T;
    }

    const text = await response.text();
    if (!text) return {} as T;
    
    return JSON.parse(text) as T;
  }

  async get<T>(endpoint: string, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async post<T>(endpoint: string, body?: any, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async put<T>(endpoint: string, body?: any, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async patch<T>(endpoint: string, body?: any, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(endpoint: string, options?: ApiClientOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
