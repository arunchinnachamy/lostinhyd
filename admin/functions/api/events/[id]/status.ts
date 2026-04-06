/**
 * PATCH /api/events/:id/status
 * Update event status (approve/reject shortcut).
 */
import { withDb } from "../../../lib/db.js";
import { updateStatus } from "../../../lib/crud.js";
import { handleError } from "../../../lib/errors.js";

export const onRequestPatch: PagesFunction<Env, "id"> = async (context) => {
  try {
    const id = context.params.id as string;
    const body = (await context.request.json()) as { status?: string };

    if (!body.status) {
      return Response.json({ error: "status is required" }, { status: 400 });
    }

    return await withDb(context.env, async (client) => {
      const record = await updateStatus(client, "events", id, body.status!);
      return Response.json(record);
    });
  } catch (error) {
    return handleError(error);
  }
};
