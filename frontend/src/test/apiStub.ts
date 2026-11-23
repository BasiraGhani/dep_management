import {
  AxiosError,
  AxiosHeaders,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';

import { api } from '../api/client';

export interface StubbedCall {
  method: string;
  url: string;
  params: unknown;
  data: unknown;
  headers: AxiosHeaders;
  responseType?: string;
}

/**
 * Replace the API client's network adapter: every request is recorded and answered
 * with `status` and `data`. Non-2xx statuses reject like a real server response.
 * Returns the recorded calls; call `restore()` afterwards.
 */
export function stubApi(status = 200, data: unknown = {}) {
  const calls: StubbedCall[] = [];
  const original = api.defaults.adapter;
  api.defaults.adapter = (config: InternalAxiosRequestConfig) => {
    calls.push({
      method: (config.method ?? 'get').toUpperCase(),
      url: config.url ?? '',
      params: config.params,
      data: config.data,
      headers: AxiosHeaders.from(config.headers),
      responseType: config.responseType,
    });
    const response: AxiosResponse = {
      data,
      status,
      statusText: String(status),
      headers: {},
      config,
    };
    if (status >= 200 && status < 300) return Promise.resolve(response);
    return Promise.reject(
      new AxiosError(
        `Request failed with status ${status}`,
        'ERR_BAD_REQUEST',
        config,
        null,
        response,
      ),
    );
  };
  return {
    calls,
    restore: () => {
      api.defaults.adapter = original;
    },
  };
}
