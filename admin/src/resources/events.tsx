/**
 * Event resource: list with approve/reject actions, edit form.
 * Matches the real lostinhyd.events schema (integer IDs, start_date/start_time, etc.)
 */
import {
  List,
  Datagrid,
  TextField,
  DateField,
  BooleanField,
  FunctionField,
  EditButton,
  Edit,
  SimpleForm,
  TextInput,
  DateInput,
  TimeInput,
  SelectInput,
  BooleanInput,
  NumberInput,
  BulkUpdateButton,
  useRecordContext,
  TopToolbar,
  FilterButton,
  Button,
  useUpdate,
  useNotify,
  useRefresh,
} from "react-admin";

const STATUS_CHOICES = [
  { id: "draft", name: "Draft" },
  { id: "published", name: "Published" },
  { id: "rejected", name: "Rejected" },
  { id: "archived", name: "Archived" },
];

function ApproveButton() {
  const record = useRecordContext();
  const [update] = useUpdate();
  const notify = useNotify();
  const refresh = useRefresh();

  if (!record || record.status === "published") return null;

  const handleClick = () => {
    update(
      "events",
      { id: record.id, data: { status: "published" }, previousData: record },
      {
        onSuccess: () => {
          notify("Event approved");
          refresh();
        },
      },
    );
  };

  return (
    <Button label="Approve" onClick={handleClick} color="success" />
  );
}

function RejectButton() {
  const record = useRecordContext();
  const [update] = useUpdate();
  const notify = useNotify();
  const refresh = useRefresh();

  if (!record || record.status === "rejected") return null;

  const handleClick = () => {
    update(
      "events",
      { id: record.id, data: { status: "rejected" }, previousData: record },
      {
        onSuccess: () => {
          notify("Event rejected");
          refresh();
        },
      },
    );
  };

  return (
    <Button label="Reject" onClick={handleClick} color="error" />
  );
}

const eventFilters = [
  <SelectInput key="status" source="status" choices={STATUS_CHOICES} alwaysOn />,
  <TextInput key="q" source="q" label="Search" alwaysOn />,
];

const EventBulkActions = () => (
  <>
    <BulkUpdateButton
      label="Approve Selected"
      data={{ status: "published" }}
      mutationMode="pessimistic"
    />
    <BulkUpdateButton
      label="Reject Selected"
      data={{ status: "rejected" }}
      mutationMode="pessimistic"
    />
  </>
);

const EventListActions = () => (
  <TopToolbar>
    <FilterButton />
  </TopToolbar>
);

export function EventList() {
  return (
    <List
      filters={eventFilters}
      actions={<EventListActions />}
      sort={{ field: "created_at", order: "DESC" }}
      filterDefaultValues={{ status: "draft" }}
    >
      <Datagrid bulkActionButtons={<EventBulkActions />}>
        <TextField source="title" />
        <DateField source="start_date" />
        <TextField source="venue_name" />
        <TextField source="organizer" />
        <BooleanField source="is_free" />
        <BooleanField source="is_featured" />
        <FunctionField
          source="status"
          render={(record: { status: string }) => {
            const colors: Record<string, string> = {
              draft: "#f59e0b",
              published: "#10b981",
              rejected: "#ef4444",
              archived: "#6b7280",
            };
            return (
              <span style={{ color: colors[record.status] || "#6b7280", fontWeight: 600 }}>
                {record.status}
              </span>
            );
          }}
        />
        <DateField source="created_at" showTime />
        <ApproveButton />
        <RejectButton />
        <EditButton />
      </Datagrid>
    </List>
  );
}

export function EventEdit() {
  return (
    <Edit>
      <SimpleForm>
        <TextInput source="title" fullWidth />
        <TextInput source="slug" fullWidth />
        <TextInput source="description" multiline fullWidth rows={4} />
        <TextInput source="content" multiline fullWidth rows={6} />
        <DateInput source="start_date" />
        <TimeInput source="start_time" />
        <DateInput source="end_date" />
        <TimeInput source="end_time" />
        <TextInput source="timezone" defaultValue="Asia/Kolkata" />
        <BooleanInput source="is_recurring" />
        <TextInput source="recurrence_pattern" />
        <TextInput source="venue_name" fullWidth />
        <TextInput source="venue_address" fullWidth />
        <BooleanInput source="is_online" />
        <TextInput source="online_url" fullWidth />
        <TextInput source="image_url" fullWidth />
        <BooleanInput source="is_free" />
        <NumberInput source="price_min" />
        <NumberInput source="price_max" />
        <TextInput source="currency" defaultValue="INR" />
        <TextInput source="ticket_url" fullWidth />
        <TextInput source="age_limit" />
        <TextInput source="organizer" fullWidth />
        <SelectInput source="status" choices={STATUS_CHOICES} />
        <BooleanInput source="is_featured" />
        <TextInput source="meta_title" fullWidth />
        <TextInput source="meta_description" multiline fullWidth rows={2} />

        {/* Read-only source metadata */}
        <NumberInput source="source_id" disabled />
        <TextInput source="source_url" disabled fullWidth />
        <TextInput source="source_event_id" disabled />
      </SimpleForm>
    </Edit>
  );
}
