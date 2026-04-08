/**
 * Database connection helper for Express server.
 * Connects to PostgreSQL using DATABASE_URL from environment.
 */
import pg from "pg";

const { Client } = pg;

export function createClient() {
  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error(
      "No database connection available. Set DATABASE_URL environment variable.",
    );
  }

  // OVH uses self-signed certs
  const isOvh = databaseUrl.includes("ovh.net");
  const connectionString = isOvh
    ? databaseUrl.replace(/[?&]sslmode=[^&]*/, "")
    : databaseUrl;

  return new Client({
    connectionString,
    ssl: isOvh ? { rejectUnauthorized: false } : false,
  });
}

/**
 * Execute a callback with a connected database client.
 * Automatically connects before and disconnects after.
 */
export async function withDb(fn) {
  const client = createClient();
  await client.connect();
  try {
    await client.query("SET search_path TO lostinhyd, public");
    return await fn(client);
  } finally {
    await client.end();
  }
}
