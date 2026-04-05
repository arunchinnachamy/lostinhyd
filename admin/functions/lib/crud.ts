/**
 * Shared CRUD helper for events, venues, and sources.
 * Generates parameterized queries with column whitelisting for sort fields.
 *
 * Matches the real lostinhyd schema (integer IDs, actual column names).
 */
import type pg from "pg";
import { badRequest, notFound } from "./errors.js";

/** Valid sortable columns per table. Prevents SQL injection via sort params. */
const SORTABLE_COLUMNS: Record<string, Set<string>> = {
  events: new Set([
    "id", "title", "start_date", "end_date", "venue_name", "status",
    "is_featured", "organizer", "created_at", "updated_at",
  ]),
  venues: new Set([
    "id", "name", "area", "city", "created_at", "updated_at",
  ]),
  sources: new Set([
    "id", "name", "source_type", "crawl_frequency", "last_crawled",
    "is_active", "created_at",
  ]),
  crawl_logs: new Set([
    "id", "started_at", "completed_at", "events_found", "events_added",
    "status",
  ]),
};

/** Valid filter columns per table. */
const FILTERABLE_COLUMNS: Record<string, Set<string>> = {
  events: new Set(["status", "source_id", "venue_id", "is_featured", "is_free"]),
  venues: new Set(["area", "city"]),
  sources: new Set(["is_active", "source_type"]),
  crawl_logs: new Set(["status", "source_id"]),
};

interface ListParams {
  _sort?: string;
  _order?: string;
  _start?: string;
  _end?: string;
  [key: string]: string | undefined;
}

/**
 * List records with filtering, sorting, and pagination.
 * Compatible with ra-data-simple-rest conventions.
 */
export async function listRecords(
  client: pg.Client,
  table: string,
  params: ListParams,
): Promise<{ rows: Record<string, unknown>[]; total: number }> {
  const sortable = SORTABLE_COLUMNS[table];
  const filterable = FILTERABLE_COLUMNS[table];
  if (!sortable || !filterable) {
    throw badRequest(`Unknown table: ${table}`);
  }

  const conditions: string[] = [];
  const values: unknown[] = [];
  let paramIdx = 1;

  // Apply filters from query params
  for (const [key, value] of Object.entries(params)) {
    if (key.startsWith("_") || value === undefined) continue;

    if (key === "q" || key === "search") {
      // Text search on title/name
      const nameCol = table === "events" ? "title" : "name";
      conditions.push(`${nameCol} ILIKE $${paramIdx}`);
      values.push(`%${value}%`);
      paramIdx++;
      continue;
    }

    if (!filterable.has(key)) continue;
    conditions.push(`${key} = $${paramIdx}`);
    values.push(value);
    paramIdx++;
  }

  const whereClause =
    conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  // Count total
  const countResult = await client.query(
    `SELECT COUNT(*)::int AS total FROM ${table} ${whereClause}`,
    values,
  );
  const total = countResult.rows[0].total;

  // Sort — default column varies by table (crawl_logs has no created_at)
  const defaultSort = table === "crawl_logs" ? "started_at" : "created_at";
  const sortField = params._sort && sortable.has(params._sort) ? params._sort : defaultSort;
  const sortOrder = params._order?.toUpperCase() === "ASC" ? "ASC" : "DESC";

  // Pagination (ra-data-simple-rest uses _start/_end)
  const start = parseInt(params._start ?? "0", 10);
  const end = parseInt(params._end ?? "25", 10);
  const limit = end - start;
  const offset = start;

  const dataResult = await client.query(
    `SELECT * FROM ${table} ${whereClause}
     ORDER BY ${sortField} ${sortOrder}
     LIMIT $${paramIdx} OFFSET $${paramIdx + 1}`,
    [...values, limit, offset],
  );

  return { rows: dataResult.rows, total };
}

/**
 * Get a single record by integer ID.
 */
export async function getRecord(
  client: pg.Client,
  table: string,
  id: string | number,
): Promise<Record<string, unknown>> {
  const result = await client.query(
    `SELECT * FROM ${table} WHERE id = $1`,
    [id],
  );

  if (result.rows.length === 0) {
    throw notFound(`${table} record`);
  }

  return result.rows[0];
}

/** Columns that can be updated via PUT for each table. */
const UPDATABLE_COLUMNS: Record<string, string[]> = {
  events: [
    "title", "slug", "description", "content", "start_date", "start_time",
    "end_date", "end_time", "timezone", "is_recurring", "recurrence_pattern",
    "venue_id", "venue_name", "venue_address", "is_online", "online_url",
    "source_url", "image_url", "is_free", "price_min", "price_max",
    "currency", "ticket_url", "age_limit", "organizer", "tags",
    "status", "is_featured", "meta_title", "meta_description",
  ],
  venues: [
    "name", "address", "city", "area", "state", "country", "pincode",
    "latitude", "longitude", "phone", "website", "google_maps_url",
  ],
  sources: [
    "url", "source_type", "crawl_frequency", "is_active",
  ],
};

/**
 * Update a record by integer ID. Only updates whitelisted columns present in the body.
 */
export async function updateRecord(
  client: pg.Client,
  table: string,
  id: string | number,
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const allowed = UPDATABLE_COLUMNS[table];
  if (!allowed) {
    throw badRequest(`Updates not supported for table: ${table}`);
  }

  const setClauses: string[] = [];
  const values: unknown[] = [];
  let paramIdx = 1;

  for (const col of allowed) {
    if (col in data) {
      setClauses.push(`${col} = $${paramIdx}`);
      values.push(data[col]);
      paramIdx++;
    }
  }

  if (setClauses.length === 0) {
    throw badRequest("No valid fields to update");
  }

  // Auto-update updated_at
  setClauses.push(`updated_at = CURRENT_TIMESTAMP`);

  values.push(id);
  const result = await client.query(
    `UPDATE ${table} SET ${setClauses.join(", ")}
     WHERE id = $${paramIdx}
     RETURNING *`,
    values,
  );

  if (result.rows.length === 0) {
    throw notFound(`${table} record`);
  }

  return result.rows[0];
}

/**
 * Update the status of a single event.
 */
export async function updateStatus(
  client: pg.Client,
  table: string,
  id: string | number,
  status: string,
): Promise<Record<string, unknown>> {
  const validStatuses = ["draft", "published", "rejected", "archived"];
  if (!validStatuses.includes(status)) {
    throw badRequest(`Invalid status: ${status}. Must be one of: ${validStatuses.join(", ")}`);
  }

  const result = await client.query(
    `UPDATE ${table} SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2 RETURNING *`,
    [status, id],
  );

  if (result.rows.length === 0) {
    throw notFound(`${table} record`);
  }

  return result.rows[0];
}

/**
 * Batch update status for multiple records.
 * Returns count of updated records.
 */
export async function batchUpdateStatus(
  client: pg.Client,
  table: string,
  ids: (string | number)[],
  status: string,
): Promise<{ updated: number }> {
  if (!ids || ids.length === 0) {
    throw badRequest("ids array is required and must not be empty");
  }

  const validStatuses = ["draft", "published", "rejected", "archived"];
  if (!validStatuses.includes(status)) {
    throw badRequest(`Invalid status: ${status}`);
  }

  const result = await client.query(
    `UPDATE ${table} SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = ANY($2::int[])`,
    [status, ids],
  );

  return { updated: result.rowCount ?? 0 };
}
