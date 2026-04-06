/**
 * Crawl log monitoring resource. Read-only list with stats.
 * Matches lostinhyd.crawl_logs schema.
 */
import {
  List,
  Datagrid,
  TextField,
  DateField,
  NumberField,
  FunctionField,
  TextInput,
  SelectInput,
  FilterButton,
  TopToolbar,
} from "react-admin";

const logFilters = [
  <SelectInput
    key="status"
    source="status"
    choices={[
      { id: "success", name: "Success" },
      { id: "failed", name: "Failed" },
      { id: "running", name: "Running" },
    ]}
    alwaysOn
  />,
  <TextInput key="source_id" source="source_id" label="Source ID" />,
];

export function CrawlLogList() {
  return (
    <List
      filters={logFilters}
      actions={<TopToolbar><FilterButton /></TopToolbar>}
      sort={{ field: "started_at", order: "DESC" }}
    >
      <Datagrid bulkActionButtons={false}>
        <TextField source="source_name" label="Source" />
        <DateField source="started_at" showTime />
        <DateField source="completed_at" showTime label="Completed" />
        <FunctionField
          label="Duration"
          render={(record: { started_at?: string; completed_at?: string }) => {
            if (!record.started_at || !record.completed_at) return "-";
            const ms =
              new Date(record.completed_at).getTime() -
              new Date(record.started_at).getTime();
            return `${Math.round(ms / 1000)}s`;
          }}
        />
        <NumberField source="events_found" />
        <NumberField source="events_added" label="New" />
        <NumberField source="events_updated" />
        <NumberField source="events_skipped" label="Skipped" />
        <FunctionField
          source="status"
          render={(record: { status: string }) => {
            const colors: Record<string, string> = {
              success: "#10b981",
              failed: "#ef4444",
              running: "#f59e0b",
            };
            return (
              <span style={{ color: colors[record.status] || "#6b7280", fontWeight: 600 }}>
                {record.status}
              </span>
            );
          }}
        />
        <TextField source="errors" label="Errors" />
      </Datagrid>
    </List>
  );
}
