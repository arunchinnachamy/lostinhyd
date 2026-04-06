/**
 * PATCH /api/events/batch-status
 * Bulk update status for multiple events.
 */
import { withDb } from "../../lib/db.js";
import { batchUpdateStatus } from "../../lib/crud.js";
import { handleError } from "../../lib/errors.js";

export const onRequestPatch: PagesFunction<Env> = async (context) => {
  try {
    const body = (await context.request.json()) as {
      ids?: string[];
      status?: string;
    };

    if (!body.ids || !body.status) {
      return Response.json(
        { error: "ids (array) and status are required" },
        { status: 400 },
      );
    }

    return await withDb(context.env, async (client) => {
      const result = await batchUpdateStatus(
        client,
        "events",
        body.ids!,
        body.status!,
      );
      return Response.json(result);
    });
  } catch (error) {
    return handleError(error);
  }
};
