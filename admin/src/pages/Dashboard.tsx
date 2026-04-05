/**
 * Dashboard with summary cards.
 * Fetches stats from /api/crawl-logs/stats and event counts.
 */
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader } from "@mui/material";
import { Title, useDataProvider } from "react-admin";
import { getAuthToken } from "../authProvider";

interface CrawlStats {
  total_runs_24h: number;
  total_runs_7d: number;
  success_rate_7d: number;
  events_found_7d: number;
  last_run_per_source: Array<{
    source_name: string;
    started_at: string;
    status: string;
    events_found: number;
    events_added: number;
  }>;
}

export function Dashboard() {
  const [stats, setStats] = useState<CrawlStats | null>(null);
  const [draftCount, setDraftCount] = useState<number>(0);
  const dataProvider = useDataProvider();

  useEffect(() => {
    const token = getAuthToken();
    const headers: HeadersInit = token
      ? { Authorization: `Bearer ${token}` }
      : {};

    fetch("/api/crawl-logs/stats", { headers })
      .then((r) => r.json())
      .then(setStats)
      .catch(console.error);

    dataProvider
      .getList("events", {
        pagination: { page: 1, perPage: 1 },
        sort: { field: "created_at", order: "DESC" },
        filter: { status: "draft" },
      })
      .then(({ total }) => setDraftCount(total ?? 0))
      .catch(console.error);
  }, [dataProvider]);

  return (
    <div style={{ padding: 16 }}>
      <Title title="Dashboard" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
        <Card>
          <CardHeader title="Draft Events" />
          <CardContent>
            <div style={{ fontSize: 48, fontWeight: 700, color: "#f59e0b" }}>
              {draftCount}
            </div>
            <div>events awaiting review</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Crawl Runs (24h)" />
          <CardContent>
            <div style={{ fontSize: 48, fontWeight: 700 }}>
              {stats?.total_runs_24h ?? "-"}
            </div>
            <div>crawler executions</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Success Rate (7d)" />
          <CardContent>
            <div
              style={{
                fontSize: 48,
                fontWeight: 700,
                color: (stats?.success_rate_7d ?? 0) >= 80 ? "#10b981" : "#ef4444",
              }}
            >
              {stats ? `${stats.success_rate_7d}%` : "-"}
            </div>
            <div>of crawl runs succeeded</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Events Found (7d)" />
          <CardContent>
            <div style={{ fontSize: 48, fontWeight: 700 }}>
              {stats?.events_found_7d ?? "-"}
            </div>
            <div>events discovered by crawlers</div>
          </CardContent>
        </Card>
      </div>

      {stats?.last_run_per_source && stats.last_run_per_source.length > 0 && (
        <Card style={{ marginTop: 24 }}>
          <CardHeader title="Last Crawl per Source" />
          <CardContent>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
                  <th style={{ textAlign: "left", padding: 8 }}>Source</th>
                  <th style={{ textAlign: "left", padding: 8 }}>Last Run</th>
                  <th style={{ textAlign: "left", padding: 8 }}>Status</th>
                  <th style={{ textAlign: "right", padding: 8 }}>Found</th>
                  <th style={{ textAlign: "right", padding: 8 }}>Added</th>
                </tr>
              </thead>
              <tbody>
                {stats.last_run_per_source.map((source) => (
                  <tr key={source.source_name} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: 8 }}>{source.source_name}</td>
                    <td style={{ padding: 8 }}>
                      {new Date(source.started_at).toLocaleString()}
                    </td>
                    <td style={{ padding: 8 }}>
                      <span
                        style={{
                          color: source.status === "success" ? "#10b981" : "#ef4444",
                          fontWeight: 600,
                        }}
                      >
                        {source.status}
                      </span>
                    </td>
                    <td style={{ padding: 8, textAlign: "right" }}>{source.events_found}</td>
                    <td style={{ padding: 8, textAlign: "right" }}>{source.events_added}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
