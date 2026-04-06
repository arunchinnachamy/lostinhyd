/**
 * Test setup: connects to real PG, seeds data, cleans up after.
 * Requires DATABASE_URL env var pointing to the test database.
 *
 * Uses schema "lostinhyd" on the toolradar database.
 * Real schema uses integer IDs with sequences.
 */
import pg from "pg";
import { beforeAll, afterAll, beforeEach } from "vitest";

const { Client } = pg;

export let testClient: pg.Client;

/** Seed IDs are assigned by the DB sequences. We track them here after insert. */
export const SEED: {
  eventId1: number;
  eventId2: number;
  eventId3: number;
  venueId1: number;
  sourceId1: number;
  logId1: number;
  logId2: number;
} = {
  eventId1: 0,
  eventId2: 0,
  eventId3: 0,
  venueId1: 0,
  sourceId1: 0,
  logId1: 0,
  logId2: 0,
};

const ADMIN_TOKEN = "test-admin-token-123";

export function getTestEnv(): Env {
  return {
    ADMIN_TOKEN,
    DATABASE_URL: process.env.DATABASE_URL!,
  } as Env;
}

export function getAuthHeader(): string {
  return `Bearer ${ADMIN_TOKEN}`;
}

async function seedDatabase(client: pg.Client): Promise<void> {
  // Seed source
  const srcRes = await client.query(`
    INSERT INTO sources (name, url, source_type, is_active, crawl_frequency)
    VALUES ('TestSource', 'https://example.com', 'website', true, 'daily')
    RETURNING id
  `);
  SEED.sourceId1 = srcRes.rows[0].id;

  // Seed venue
  const venRes = await client.query(`
    INSERT INTO venues (name, address, city, area)
    VALUES ('Test Venue', '123 Main St', 'Hyderabad', 'Banjara Hills')
    RETURNING id
  `);
  SEED.venueId1 = venRes.rows[0].id;

  // Seed events (use random suffix to avoid slug uniqueness conflicts)
  const ts = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const evRes = await client.query(`
    INSERT INTO events (title, slug, description, start_date, venue_name, venue_id, source_id, source_url, source_event_id, status)
    VALUES
      ('Draft Event', $3, 'A draft event', CURRENT_DATE + 1, 'Test Venue', $1, $2, 'http://example.com/1', 'src-1', 'draft'),
      ('Published Event', $4, 'A published event', CURRENT_DATE + 2, 'Test Venue', $1, $2, 'http://example.com/2', 'src-2', 'published'),
      ('Rejected Event', $5, 'A rejected event', CURRENT_DATE + 3, 'Test Venue', $1, $2, 'http://example.com/3', 'src-3', 'rejected')
    RETURNING id
  `, [SEED.venueId1, SEED.sourceId1, `draft-event-${ts}`, `published-event-${ts}`, `rejected-event-${ts}`]);
  SEED.eventId1 = evRes.rows[0].id;
  SEED.eventId2 = evRes.rows[1].id;
  SEED.eventId3 = evRes.rows[2].id;

  // Seed crawl_logs
  const logRes = await client.query(`
    INSERT INTO crawl_logs (source_id, status, events_found, events_added, events_updated, events_skipped, started_at, completed_at)
    VALUES
      ($1, 'success', 10, 5, 3, 2, CURRENT_TIMESTAMP - interval '1 hour', CURRENT_TIMESTAMP - interval '55 minutes'),
      ($1, 'failed', 0, 0, 0, 0, CURRENT_TIMESTAMP - interval '2 hours', CURRENT_TIMESTAMP - interval '1 hour 50 minutes')
    RETURNING id
  `, [SEED.sourceId1]);
  SEED.logId1 = logRes.rows[0].id;
  SEED.logId2 = logRes.rows[1].id;
}

async function cleanDatabase(client: pg.Client): Promise<void> {
  // Delete in dependency order using the tracked IDs
  if (SEED.logId1) {
    await client.query(`DELETE FROM crawl_logs WHERE id IN ($1, $2)`, [SEED.logId1, SEED.logId2]);
  }
  if (SEED.eventId1) {
    await client.query(`DELETE FROM events WHERE id IN ($1, $2, $3)`, [SEED.eventId1, SEED.eventId2, SEED.eventId3]);
  }
  if (SEED.venueId1) {
    await client.query(`DELETE FROM venues WHERE id = $1`, [SEED.venueId1]);
  }
  if (SEED.sourceId1) {
    await client.query(`DELETE FROM sources WHERE id = $1`, [SEED.sourceId1]);
  }
}

beforeAll(async () => {
  const connectionString =
    process.env.DATABASE_URL ??
    "postgresql://postgres@localhost:5432/lostinhyd";

  testClient = new Client({
    connectionString,
    ssl: connectionString.includes("sslmode=require")
      ? { rejectUnauthorized: false }
      : undefined,
  });
  await testClient.connect();
  await testClient.query("SET search_path TO lostinhyd, public");
  await seedDatabase(testClient);
});

beforeEach(async () => {
  await cleanDatabase(testClient);
  await seedDatabase(testClient);
});

afterAll(async () => {
  await cleanDatabase(testClient);
  await testClient.end();
});
