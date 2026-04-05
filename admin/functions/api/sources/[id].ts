/**
 * GET /api/sources/:id  -- Get single source
 * PUT /api/sources/:id  -- Update source config
 */
import { withDb } from "../../lib/db.js";
import { getRecord, updateRecord } from "../../lib/crud.js";
import { handleError } from "../../lib/errors.js";

export const onRequestGet: PagesFunction<Env, "id"> = async (context) => {
  try {
    const id = context.params.id as string;
    return await withDb(context.env, async (client) => {
      const record = await getRecord(client, "sources", id);
      return Response.json(record);
    });
  } catch (error) {
    return handleError(error);
  }
};

export const onRequestPut: PagesFunction<Env, "id"> = async (context) => {
  try {
    const id = context.params.id as string;
    const body = (await context.request.json()) as Record<string, unknown>;
    return await withDb(context.env, async (client) => {
      const record = await updateRecord(client, "sources", id, body);
      return Response.json(record);
    });
  } catch (error) {
    return handleError(error);
  }
};
