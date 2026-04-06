/**
 * Tests for Venues CRUD operations.
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

describe("listRecords(venues)", () => {
  it("returns all venues", async () => {
    const { rows, total } = await listRecords(client, "venues", {});
    expect(total).toBeGreaterThanOrEqual(1);
    expect(rows.length).toBeGreaterThanOrEqual(1);
  });

  it("filters by area", async () => {
    const { rows } = await listRecords(client, "venues", { area: "Banjara Hills" });
    expect(rows.length).toBeGreaterThanOrEqual(1);
    for (const row of rows) {
      expect(row.area).toBe("Banjara Hills");
    }
  });

  it("supports text search (searches name column)", async () => {
    const { rows } = await listRecords(client, "venues", { q: "Test Venue" });
    expect(rows.length).toBeGreaterThanOrEqual(1);
    expect(rows.some((r) => (r.name as string).includes("Test Venue"))).toBe(true);
  });

  it("sorts by name ASC", async () => {
    const { rows } = await listRecords(client, "venues", {
      _sort: "name",
      _order: "ASC",
    });
    const names = rows.map((r) => r.name as string);
    const sorted = [...names].sort();
    expect(names).toEqual(sorted);
  });
});

describe("getRecord(venues)", () => {
  it("returns a single venue", async () => {
    const record = await getRecord(client, "venues", SEED.venueId1);
    expect(record.id).toBe(SEED.venueId1);
    expect(record.name).toBe("Test Venue");
  });

  it("throws 404 for non-existent id", async () => {
    await expect(
      getRecord(client, "venues", 999999),
    ).rejects.toThrow("not found");
  });
});

describe("updateRecord(venues)", () => {
  it("updates whitelisted fields", async () => {
    const updated = await updateRecord(client, "venues", SEED.venueId1, {
      name: "Updated Venue",
      phone: "040-12345678",
    });
    expect(updated.name).toBe("Updated Venue");
    expect(updated.phone).toBe("040-12345678");
  });

  it("ignores non-whitelisted fields (e.g., id)", async () => {
    const updated = await updateRecord(client, "venues", SEED.venueId1, {
      name: "Safe Venue",
      id: 999,  // should not be updatable
    });
    expect(updated.name).toBe("Safe Venue");
    expect(updated.id).toBe(SEED.venueId1);
  });
});
