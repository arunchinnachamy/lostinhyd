/**
 * GET /api/crawl-logs
 * List crawl logs with filtering, sorting, and pagination.
 * Joins with sources to include source name.
 */
import { withDb } from "../../lib/db.js";
import { handleError } from "../../lib/errors.js";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  try {
    const url = new URL(context.request.url);
    const sourceId = url.searchParams.get("source_id");
    const status = url.searchParams.get("status");
    const start = parseInt(url.searchParams.get("_start") ?? "0", 10);
    const end = parseInt(url.searchParams.get("_end") ?? "50", 10);
    const sortField = url.searchParams.get("_sort") ?? "started_at";
    const sortOrder =
      url.searchParams.get("_order")?.toUpperCase() === "ASC" ? "ASC" : "DESC";

    // Whitelist sort fields
    const validSorts = new Set([
      "started_at", "completed_at", "events_found", "events_added", "status",
    ]);
    const safeSortField = validSorts.has(sortField) ? sortField : "started_at";

    return await withDb(context.env, async (client) => {
      const conditions: string[] = [];
      const values: unknown[] = [];
      let paramIdx = 1;

      if (sourceId) {
        conditions.push(`cl.source_id = $${paramIdx}`);
        values.push(sourceId);
        paramIdx++;
      }
      if (status) {
        conditions.push(`cl.status = $${paramIdx}`);
        values.push(status);
        paramIdx++;
      }

      const whereClause =
        conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

      const countResult = await client.query(
        `SELECT COUNT(*)::int AS total FROM crawl_logs cl ${whereClause}`,
        values,
      );
      const total = countResult.rows[0].total;

      const limit = end - start;
      const dataResult = await client.query(
        `SELECT cl.*, s.name AS source_name
         FROM crawl_logs cl
         LEFT JOIN sources s ON cl.source_id = s.id
         ${whereClause}
         ORDER BY cl.${safeSortField} ${sortOrder}
         LIMIT $${paramIdx} OFFSET $${paramIdx + 1}`,
        [...values, limit, start],
      );

      return new Response(JSON.stringify(dataResult.rows), {
        headers: {
          "Content-Type": "application/json",
          "X-Total-Count": String(total),
          "Access-Control-Expose-Headers": "X-Total-Count",
        },
      });
    });
  } catch (error) {
    return handleError(error);
  }
};
