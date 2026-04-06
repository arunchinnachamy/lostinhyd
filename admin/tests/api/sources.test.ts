/**
 * Tests for Sources CRUD operations.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import pg from "pg";
import { createTestClient } from "../helpers.js";
import { SEED } from "../setup.js";
import {
  listRecords,
  getRecord,
  updateRecord,
} from "../../functions/lib/crud.js";

let client: pg.Client;

beforeAll(async () => {
  client = await createTestClient();
});

afterAll(async () => {
  if (client) await client.end();
});

describe("listRecords(sources)", () => {
  it("returns all sources", async () => {
    const { rows, total } = await listRecords(client, "sources", {});
    expect(total).toBeGreaterThanOrEqual(1);
    expect(rows.length).toBeGreaterThanOrEqual(1);
  });

  it("filters by is_active", async () => {
    const { rows } = await listRecords(client, "sources", { is_active: "true" });
    for (const row of rows) {
      expect(row.is_active).toBe(true);
    }
  });

  it("sorts by name ASC", async () => {
    const { rows } = await listRecords(client, "sources", {
      _sort: "name",
      _order: "ASC",
    });
    const names = rows.map((r) => r.name as string);
    const sorted = [...names].sort();
    expect(names).toEqual(sorted);
  });
});

describe("getRecord(sources)", () => {
  it("returns a single source", async () => {
    const record = await getRecord(client, "sources", SEED.sourceId1);
    expect(record.id).toBe(SEED.sourceId1);
    expect(record.name).toBe("TestSource");
  });
});

describe("updateRecord(sources)", () => {
  it("updates url and crawl_frequency", async () => {
    const updated = await updateRecord(client, "sources", SEED.sourceId1, {
      url: "https://updated-example.com",
      crawl_frequency: "hourly",
    });
    expect(updated.url).toBe("https://updated-example.com");
    expect(updated.crawl_frequency).toBe("hourly");
  });

  it("updates is_active toggle", async () => {
    const updated = await updateRecord(client, "sources", SEED.sourceId1, {
      is_active: false,
    });
    expect(updated.is_active).toBe(false);
  });

  it("ignores non-whitelisted fields (e.g., name)", async () => {
    const updated = await updateRecord(client, "sources", SEED.sourceId1, {
      url: "https://safe.com",
      name: "hacked-name",
    });
    expect(updated.url).toBe("https://safe.com");
    expect(updated.name).toBe("TestSource");
  });
});
