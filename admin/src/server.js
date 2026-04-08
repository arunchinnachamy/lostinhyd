/**
 * Express API Server for Lost in Hyd Admin
 * Replaces Cloudflare Pages Functions
 */
import express from "express";
import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";
import { withDb } from "./db.js";
import { handleError } from "./lib/errors.js";
import {
  listRecords,
  getRecord,
  updateRecord,
  updateStatus,
  batchUpdateStatus,
} from "./lib/crud.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Request logging in development
if (process.env.NODE_ENV !== "production") {
  app.use((req, res, next) => {
    console.log(`${req.method} ${req.path}`);
    next();
  });
}

// Auth middleware (skip for /api/auth/verify)
const authMiddleware = (req, res, next) => {
  if (req.path === "/api/auth/verify") {
    return next();
  }

  const authHeader = req.headers.authorization;
  const token = authHeader?.startsWith("Bearer ")
    ? authHeader.slice(7)
    : null;

  if (!token || token !== process.env.ADMIN_TOKEN) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  next();
};

app.use(authMiddleware);

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({ status: "healthy", service: "admin-api" });
});

// ====================
// Events Routes
// ====================

// GET /api/events - List events
app.get("/api/events", async (req, res, next) => {
  try {
    const result = await withDb(async (client) => {
      return await listRecords(client, "events", req.query);
    });

    res.setHeader("X-Total-Count", result.total);
    res.setHeader("Access-Control-Expose-Headers", "X-Total-Count");
    res.json(result.rows);
  } catch (error) {
    next(error);
  }
});

// GET /api/events/:id - Get single event
app.get("/api/events/:id", async (req, res, next) => {
  try {
    const record = await withDb(async (client) => {
      return await getRecord(client, "events", req.params.id);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// PUT /api/events/:id - Update event
app.put("/api/events/:id", async (req, res, next) => {
  try {
    const record = await withDb(async (client) => {
      return await updateRecord(client, "events", req.params.id, req.body);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// PUT /api/events/:id/status - Update event status
app.put("/api/events/:id/status", async (req, res, next) => {
  try {
    const { status } = req.body;
    const record = await withDb(async (client) => {
      return await updateStatus(client, "events", req.params.id, status);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// PUT /api/events/batch-status - Batch update event status
app.put("/api/events/batch-status", async (req, res, next) => {
  try {
    const { ids, status } = req.body;
    const result = await withDb(async (client) => {
      return await batchUpdateStatus(client, "events", ids, status);
    });
    res.json(result);
  } catch (error) {
    next(error);
  }
});

// ====================
// Venues Routes
// ====================

// GET /api/venues - List venues
app.get("/api/venues", async (req, res, next) => {
  try {
    const result = await withDb(async (client) => {
      return await listRecords(client, "venues", req.query);
    });

    res.setHeader("X-Total-Count", result.total);
    res.setHeader("Access-Control-Expose-Headers", "X-Total-Count");
    res.json(result.rows);
  } catch (error) {
    next(error);
  }
});

// GET /api/venues/:id - Get single venue
app.get("/api/venues/:id", async (req, res, next) => {
  try {
    const record = await withDb(async (client) => {
      return await getRecord(client, "venues", req.params.id);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// PUT /api/venues/:id - Update venue
app.put("/api/venues/:id", async (req, res, next) => {
  try {
    const record = await withDb(async (client) => {
      return await updateRecord(client, "venues", req.params.id, req.body);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// ====================
// Sources Routes
// ====================

// GET /api/sources - List sources
app.get("/api/sources", async (req, res, next) => {
  try {
    const result = await withDb(async (client) => {
      return await listRecords(client, "sources", req.query);
    });

    res.setHeader("X-Total-Count", result.total);
    res.setHeader("Access-Control-Expose-Headers", "X-Total-Count");
    res.json(result.rows);
  } catch (error) {
    next(error);
  }
});

// GET /api/sources/:id - Get single source
app.get("/api/sources/:id", async (req, res, next) => {
  try {
    const record = await withDb(async (client) => {
      return await getRecord(client, "sources", req.params.id);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// PUT /api/sources/:id - Update source
app.put("/api/sources/:id", async (req, res, next) => {
  try {
    const record = await withDb(async (client) => {
      return await updateRecord(client, "sources", req.params.id, req.body);
    });
    res.json(record);
  } catch (error) {
    next(error);
  }
});

// ====================
// Crawl Logs Routes
// ====================

// GET /api/crawl-logs - List crawl logs
app.get("/api/crawl-logs", async (req, res, next) => {
  try {
    const result = await withDb(async (client) => {
      return await listRecords(client, "crawl_logs", req.query);
    });

    res.setHeader("X-Total-Count", result.total);
    res.setHeader("Access-Control-Expose-Headers", "X-Total-Count");
    res.json(result.rows);
  } catch (error) {
    next(error);
  }
});

// GET /api/crawl-logs/stats - Aggregated crawl statistics
app.get("/api/crawl-logs/stats", async (req, res, next) => {
  try {
    const stats = await withDb(async (client) => {
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

      return {
        total_runs_24h: runs24h.rows[0].count,
        total_runs_7d: totalRuns7d,
        success_rate_7d:
          totalRuns7d > 0
            ? Math.round((successRuns7d / totalRuns7d) * 100)
            : 0,
        events_found_7d: eventsFound7d.rows[0].count,
        last_run_per_source: lastPerSource.rows,
      };
    });

    res.json(stats);
  } catch (error) {
    next(error);
  }
});

// ====================
// Auth Routes
// ====================

// POST /api/auth/verify - Token verification (no auth required)
app.post("/api/auth/verify", (req, res) => {
  const { token } = req.body;

  if (!token) {
    return res.status(400).json({ error: "Token is required" });
  }

  if (token !== process.env.ADMIN_TOKEN) {
    return res.status(401).json({ error: "Invalid token" });
  }

  res.json({ ok: true });
});

// ====================
// Error Handler
// ====================
app.use(handleError);

// ====================
// Static File Serving (React Admin SPA)
// ====================
// Serve static files from the dist directory
app.use(express.static(path.join(__dirname, "../dist")));

// For any other route, serve the SPA (React Router handles client-side routing)
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "../dist", "index.html"));
});

// Start server
app.listen(PORT, () => {
  console.log(`Admin API server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});
