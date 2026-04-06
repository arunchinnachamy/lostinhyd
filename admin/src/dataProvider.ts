/**
 * Custom data provider wrapping ra-data-simple-rest.
 * Adds Bearer token to every request.
 */
import simpleRestProvider from "ra-data-simple-rest";
import { fetchUtils } from "react-admin";
import { getAuthToken } from "./authProvider";

const httpClient = (url: string, options: fetchUtils.Options = {}) => {
  const token = getAuthToken();
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetchUtils.fetchJson(url, { ...options, headers });
};

export const dataProvider = simpleRestProvider("/api", httpClient);
