/**
 * Test helpers: mock Cloudflare Pages context, request builders.
 */
import pg from "pg";

const { Client } = pg;

/**
 * Create a connected pg.Client for use in CRUD tests.
 * Sets search_path to lostinhyd schema.
 */
export async function createTestClient(): Promise<pg.Client> {
  const connectionString =
    process.env.DATABASE_URL ??
    "postgresql://postgres@localhost:5432/lostinhyd";

  const client = new Client({
    connectionString,
    ssl: connectionString.includes("sslmode=require")
      ? { rejectUnauthorized: false }
      : undefined,
  });
  await client.connect();
  await client.query("SET search_path TO lostinhyd, public");
  return client;
}

/**
 * Build a minimal mock Env for handler tests.
 */
export function mockEnv(overrides?: Partial<Env>): Env {
  return {
    ADMIN_TOKEN: "test-admin-token-123",
    DATABASE_URL:
      process.env.DATABASE_URL ??
      "postgresql://postgres@localhost:5432/lostinhyd",
    ...overrides,
  } as Env;
}

/**
 * Build a Request with JSON body.
 */
export function jsonRequest(
  url: string,
  method: string,
  body?: unknown,
  headers?: Record<string, string>,
): Request {
  const init: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }
  return new Request(url, init);
}
