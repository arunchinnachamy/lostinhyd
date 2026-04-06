/**
 * Tests for Crawl Logs listing and stats.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import pg from "pg";
import { createTestClient } from "../helpers.js";
import { SEED } from "../setup.js";
import { listRecords } from "../../functions/lib/crud.js";

let client: pg.Client;

beforeAll(async () => {
  client = await createTestClient();
});

afterAll(async () => {
  if (client) await client.end();
});

describe("listRecords(crawl_logs)", () => {
  it("returns crawl logs", async () => {
    const { rows, total } = await listRecords(client, "crawl_logs", {});
    expect(total).toBeGreaterThanOrEqual(2);
    expect(rows.length).toBeGreaterThanOrEqual(2);
  });

  it("filters by status", async () => {
    const { rows } = await listRecords(client, "crawl_logs", { status: "success" });
    for (const row of rows) {
      expect(row.status).toBe("success");
    }
  });

  it("filters by source_id", async () => {
    const { rows } = await listRecords(client, "crawl_logs", {
      source_id: String(SEED.sourceId1),
    });
    for (const row of rows) {
      expect(row.source_id).toBe(SEED.sourceId1);
    }
  });

  it("sorts by started_at DESC by default", async () => {
    const { rows } = await listRecords(client, "crawl_logs", {});
    if (rows.length >= 2) {
      const dates = rows.map((r) => new Date(r.started_at as string).getTime());
      for (let i = 0; i < dates.length - 1; i++) {
        expect(dates[i]).toBeGreaterThanOrEqual(dates[i + 1]);
      }
    }
  });
});

describe("crawl-logs stats query", () => {
  it("computes stats correctly", async () => {
    const now = new Date();
    const ago24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const ago7d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    const [runs24h, runs7d, success7d, eventsFound7d] = await Promise.all([
      client.query(
        `SELECT COUNT(*)::int AS count FROM crawl_logs WHERE started_at >= $1`,
        [ago24h],
      ),
      client.query(
        `SELECT COUNT(*)::int AS count FROM crawl_logs WHERE started_at >= $1`,
        [ago7d],
      ),
      client.query(
        `SELECT COUNT(*)::int AS count FROM crawl_logs WHERE started_at >= $1 AND status = 'success'`,
        [ago7d],
      ),
      client.query(
        `SELECT COALESCE(SUM(events_found), 0)::int AS count FROM crawl_logs WHERE started_at >= $1`,
        [ago7d],
      ),
    ]);

    expect(runs24h.rows[0].count).toBeGreaterThanOrEqual(2);
    expect(runs7d.rows[0].count).toBeGreaterThanOrEqual(2);
    expect(success7d.rows[0].count).toBeGreaterThanOrEqual(1);
    expect(eventsFound7d.rows[0].count).toBeGreaterThanOrEqual(10);
  });

  it("joins with sources for source name", async () => {
    const result = await client.query(
      `SELECT cl.*, s.name AS source_name
       FROM crawl_logs cl
       LEFT JOIN sources s ON cl.source_id = s.id
       WHERE cl.id = $1`,
      [SEED.logId1],
    );
    expect(result.rows.length).toBe(1);
    expect(result.rows[0].source_name).toBe("TestSource");
  });
});
