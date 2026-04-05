/**
 * React Admin auth provider.
 * Uses a Bearer token stored in localStorage.
 * Validates against /api/auth/verify on login.
 */
import type { AuthProvider } from "react-admin";

const AUTH_KEY = "lostinhyd_admin_token";

export const authProvider: AuthProvider = {
  async login({ password }: { password: string }) {
    const response = await fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: password }),
    });

    if (!response.ok) {
      throw new Error("Invalid token");
    }

    localStorage.setItem(AUTH_KEY, password);
  },

  async logout() {
    localStorage.removeItem(AUTH_KEY);
  },

  async checkAuth() {
    const token = localStorage.getItem(AUTH_KEY);
    if (!token) {
      throw new Error("Not authenticated");
    }
  },

  async checkError(error: { status?: number }) {
    if (error.status === 401) {
      localStorage.removeItem(AUTH_KEY);
      throw new Error("Session expired");
    }
  },

  async getIdentity() {
    return { id: "admin", fullName: "Admin" };
  },

  async getPermissions() {
    return "admin";
  },
};

/**
 * Get the stored auth token for API requests.
 */
export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_KEY);
}
