/**
 * GET /api/sources
 * List all crawler sources.
 */
import { withDb } from "../../lib/db.js";
import { listRecords } from "../../lib/crud.js";
import { handleError } from "../../lib/errors.js";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  try {
    const url = new URL(context.request.url);
    const params = Object.fromEntries(url.searchParams.entries());

    return await withDb(context.env, async (client) => {
      const { rows, total } = await listRecords(client, "sources", params);

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
