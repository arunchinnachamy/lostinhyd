/**
 * Tests for /api/auth/verify endpoint.
 */
import { describe, it, expect } from "vitest";
import { mockEnv, jsonRequest } from "../helpers.js";

// Import the handler directly
import { onRequestPost } from "../../functions/api/auth/verify.js";

function callVerify(body: unknown) {
  const env = mockEnv();
  const request = jsonRequest("http://localhost/api/auth/verify", "POST", body);
  const context = { request, env } as unknown as Parameters<typeof onRequestPost>[0];
  return onRequestPost(context);
}

describe("POST /api/auth/verify", () => {
  it("returns 200 for valid token", async () => {
    const res = await callVerify({ token: "test-admin-token-123" });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ ok: true });
  });

  it("returns 401 for invalid token", async () => {
    const res = await callVerify({ token: "wrong-token" });
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.error).toBe("Invalid token");
  });

  it("returns 400 when token is missing", async () => {
    const res = await callVerify({});
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe("Token is required");
  });

  it("returns 400 for invalid JSON body", async () => {
    const env = mockEnv();
    const request = new Request("http://localhost/api/auth/verify", {
      method: "POST",
      body: "not json",
      headers: { "Content-Type": "text/plain" },
    });
    const context = { request, env } as unknown as Parameters<typeof onRequestPost>[0];
    const res = await onRequestPost(context);
    expect(res.status).toBe(400);
  });
});
