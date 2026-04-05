/**
 * Tests for Events CRUD operations.
 * Tests the crud.ts functions directly against real PG.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import pg from "pg";
import { createTestClient } from "../helpers.js";
import { SEED } from "../setup.js";
import {
  listRecords,
  getRecord,
  updateRecord,
  updateStatus,
  batchUpdateStatus,
} from "../../functions/lib/crud.js";

let client: pg.Client;

beforeAll(async () => {
  client = await createTestClient();
});

afterAll(async () => {
  if (client) await client.end();
});

describe("listRecords(events)", () => {
  it("returns all events with defaults", async () => {
    const { rows, total } = await listRecords(client, "events", {});
    expect(total).toBeGreaterThanOrEqual(3);
    expect(rows.length).toBeGreaterThanOrEqual(3);
  });

  it("filters by status", async () => {
    const { rows, total } = await listRecords(client, "events", { status: "draft" });
    expect(total).toBeGreaterThanOrEqual(1);
    for (const row of rows) {
      expect(row.status).toBe("draft");
    }
  });

  it("supports text search via q param", async () => {
    const { rows } = await listRecords(client, "events", { q: "Draft" });
    expect(rows.length).toBeGreaterThanOrEqual(1);
    expect(rows.some((r) => (r.title as string).includes("Draft"))).toBe(true);
  });

  it("paginates with _start/_end", async () => {
    const { rows } = await listRecords(client, "events", { _start: "0", _end: "2" });
    expect(rows.length).toBeLessThanOrEqual(2);
  });

  it("sorts by specified column", async () => {
    const { rows } = await listRecords(client, "events", {
      _sort: "title",
      _order: "ASC",
    });
    expect(rows.length).toBeGreaterThanOrEqual(2);
    const titles = rows.map((r) => r.title as string);
    const sorted = [...titles].sort();
    expect(titles).toEqual(sorted);
  });

  it("ignores unknown filter columns", async () => {
    const { rows } = await listRecords(client, "events", { malicious: "drop table" });
    expect(rows.length).toBeGreaterThanOrEqual(3);
  });

  it("falls back to default sort for invalid sort column", async () => {
    const { rows } = await listRecords(client, "events", { _sort: "'; DROP TABLE events;--" });
    expect(rows.length).toBeGreaterThanOrEqual(3);
  });

  it("throws for unknown table", async () => {
    await expect(listRecords(client, "nonexistent", {})).rejects.toThrow("Unknown table");
  });
});

describe("getRecord(events)", () => {
  it("returns a single event by id", async () => {
    const record = await getRecord(client, "events", SEED.eventId1);
    expect(record.id).toBe(SEED.eventId1);
    expect(record.title).toBe("Draft Event");
    expect(record.status).toBe("draft");
  });

  it("throws 404 for non-existent id", async () => {
    await expect(
      getRecord(client, "events", 999999),
    ).rejects.toThrow("not found");
  });
});

describe("updateRecord(events)", () => {
  it("updates whitelisted fields", async () => {
    const updated = await updateRecord(client, "events", SEED.eventId1, {
      title: "Updated Draft Event",
      venue_name: "New Venue",
    });
    expect(updated.title).toBe("Updated Draft Event");
    expect(updated.venue_name).toBe("New Venue");
  });

  it("ignores non-whitelisted fields", async () => {
    const updated = await updateRecord(client, "events", SEED.eventId1, {
      title: "Safe Update",
      source_id: 999,  // source_id is not in UPDATABLE_COLUMNS
    });
    expect(updated.title).toBe("Safe Update");
    expect(updated.source_id).toBe(SEED.sourceId1);
  });

  it("throws if no valid fields provided", async () => {
    await expect(
      updateRecord(client, "events", SEED.eventId1, { bad_field: "nope" }),
    ).rejects.toThrow("No valid fields");
  });

  it("throws 404 for non-existent id", async () => {
    await expect(
      updateRecord(client, "events", 999999, { title: "Ghost" }),
    ).rejects.toThrow("not found");
  });
});

describe("updateStatus(events)", () => {
  it("changes status to published", async () => {
    const updated = await updateStatus(client, "events", SEED.eventId1, "published");
    expect(updated.status).toBe("published");
  });

  it("changes status to rejected", async () => {
    const updated = await updateStatus(client, "events", SEED.eventId2, "rejected");
    expect(updated.status).toBe("rejected");
  });

  it("throws for invalid status", async () => {
    await expect(
      updateStatus(client, "events", SEED.eventId1, "invalid"),
    ).rejects.toThrow("Invalid status");
  });

  it("throws 404 for non-existent id", async () => {
    await expect(
      updateStatus(client, "events", 999999, "published"),
    ).rejects.toThrow("not found");
  });
});

describe("batchUpdateStatus(events)", () => {
  it("updates multiple events at once", async () => {
    const result = await batchUpdateStatus(
      client,
      "events",
      [SEED.eventId1, SEED.eventId3],
      "published",
    );
    expect(result.updated).toBe(2);

    const e1 = await getRecord(client, "events", SEED.eventId1);
    const e3 = await getRecord(client, "events", SEED.eventId3);
    expect(e1.status).toBe("published");
    expect(e3.status).toBe("published");
  });

  it("throws for empty ids array", async () => {
    await expect(
      batchUpdateStatus(client, "events", [], "published"),
    ).rejects.toThrow("ids array is required");
  });

  it("throws for invalid status", async () => {
    await expect(
      batchUpdateStatus(client, "events", [SEED.eventId1], "bogus"),
    ).rejects.toThrow("Invalid status");
  });
});
