/**
 * GET /api/events
 * List events with filtering, sorting, and pagination.
 * Compatible with ra-data-simple-rest conventions.
 */
import { withDb } from "../../lib/db.js";
import { listRecords } from "../../lib/crud.js";
import { handleError } from "../../lib/errors.js";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  try {
    const url = new URL(context.request.url);
    const params = Object.fromEntries(url.searchParams.entries());

    return await withDb(context.env, async (client) => {
      const { rows, total } = await listRecords(client, "events", params);

      return new Response(JSON.stringify(rows), {
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
