/**
 * GET /api/crawl-logs/stats
 * Aggregated crawl statistics for the dashboard.
 * Computes timestamps in Worker (not SQL NOW()) for Hyperdrive cache compatibility.
 */
import { withDb } from "../../lib/db.js";
import { handleError } from "../../lib/errors.js";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  try {
    return await withDb(context.env, async (client) => {
      const now = new Date();
      const ago24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      const ago7d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

      const [runs24h, runs7d, success7d, eventsFound7d, lastPerSource] =
        await Promise.all([
          client.query(
            `SELECT COUNT(*)::int AS count FROM crawl_logs WHERE started_at >= $1`,
            [ago24h],
          ),
          client.query(
            `SELECT COUNT(*)::int AS count FROM crawl_logs WHERE started_at >= $1`,
            [ago7d],
          ),
          client.query(
            `SELECT COUNT(*)::int AS count FROM crawl_logs
             WHERE started_at >= $1 AND status = 'success'`,
            [ago7d],
          ),
          client.query(
            `SELECT COALESCE(SUM(events_found), 0)::int AS count FROM crawl_logs
             WHERE started_at >= $1`,
            [ago7d],
          ),
          client.query(
            `SELECT DISTINCT ON (s.name)
               s.name AS source_name,
               cl.started_at,
               cl.status,
               cl.events_found,
               cl.events_added
             FROM crawl_logs cl
             JOIN sources s ON cl.source_id = s.id
             ORDER BY s.name, cl.started_at DESC`,
          ),
        ]);

      const totalRuns7d = runs7d.rows[0].count;
      const successRuns7d = success7d.rows[0].count;

      return Response.json({
        total_runs_24h: runs24h.rows[0].count,
        total_runs_7d: totalRuns7d,
        success_rate_7d:
          totalRuns7d > 0
            ? Math.round((successRuns7d / totalRuns7d) * 100)
            : 0,
        events_found_7d: eventsFound7d.rows[0].count,
        last_run_per_source: lastPerSource.rows,
      });
    });
  } catch (error) {
    return handleError(error);
  }
};
