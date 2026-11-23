import axios, { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios';

import { clearToken, getToken } from '../auth/token';
import type { ApiErrorBody } from '../types';
import { browser } from './browser';

export const DEFAULT_API_URL = 'http://localhost:8000/api/v1';
export const LOGIN_PATH = '/login';
const LOGIN_ENDPOINT = '/auth/login';

/** The one axios instance every module in src/api uses. Components never call axios. */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || DEFAULT_API_URL,
});

/** Adds `Authorization: Bearer <token>` when the user is logged in. */
export function attachToken(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const token = getToken();
  if (token) {
    const headers = AxiosHeaders.from(config.headers);
    headers.set('Authorization', `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
}

/**
 * On a 401 the session is over (expired, invalid or out-of-date token, or a
 * deactivated account): clear the token and send the user to the login page.
 * A failed login itself is left alone so the form can show the error.
 */
export function handleUnauthorized(error: unknown): Promise<never> {
  if (
    error instanceof AxiosError &&
    error.response?.status === 401 &&
    !error.config?.url?.endsWith(LOGIN_ENDPOINT)
  ) {
    clearToken();
    if (browser.currentPath() !== LOGIN_PATH) {
      browser.goTo(LOGIN_PATH);
    }
  }
  return Promise.reject(error instanceof Error ? error : new Error(String(error)));
}

api.interceptors.request.use(attachToken);
api.interceptors.response.use((response) => response, handleUnauthorized);

/** The API's error message for display, or `fallback` for network and unknown errors. */
export function errorMessage(
  error: unknown,
  fallback = 'Something went wrong. Please try again.',
): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as Partial<ApiErrorBody> | undefined)?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) return detail.map((e) => e.msg).join('; ');
    if (!error.response) return 'Cannot reach the server. Check your connection.';
  }
  return fallback;
}
