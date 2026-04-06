/**
 * Environment bindings for Cloudflare Pages Functions.
 */
interface Env {
  /** Hyperdrive binding for PostgreSQL connection pooling. */
  HYPERDRIVE: Hyperdrive;
  /** Admin authentication token. Compared against Bearer header. */
  ADMIN_TOKEN: string;
  /** Direct database URL (local dev fallback when Hyperdrive is unavailable). */
  DATABASE_URL?: string;
}
