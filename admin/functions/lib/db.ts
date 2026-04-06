/**
 * Database connection helper.
 * Uses Hyperdrive in production, falls back to DATABASE_URL for local dev.
 */
import pg from "pg";

const { Client } = pg;

export function createClient(env: Env): pg.Client {
  const raw = env.HYPERDRIVE?.connectionString ?? env.DATABASE_URL;

  if (!raw) {
    throw new Error(
      "No database connection available. Set HYPERDRIVE binding or DATABASE_URL.",
    );
  }

  // Hyperdrive handles SSL internally; for direct connections accept OVH certs.
  // Strip sslmode from URL to prevent pg-connection-string from overriding ssl config.
  const isDirectSsl = !env.HYPERDRIVE?.connectionString && raw.includes("sslmode=");
  const connectionString = isDirectSsl
    ? raw.replace(/[?&]sslmode=[^&]*/, "")
    : raw;

  return new Client({
    connectionString,
    ssl: isDirectSsl ? { rejectUnauthorized: false } : false,
  });
}

/**
 * Execute a callback with a connected database client.
 * Automatically connects before and disconnects after.
 */
export async function withDb<T>(
  env: Env,
  fn: (client: pg.Client) => Promise<T>,
): Promise<T> {
  const client = createClient(env);
  await client.connect();
  try {
    await client.query("SET search_path TO lostinhyd, public");
    return await fn(client);
  } finally {
    await client.end();
  }
}
