/**
 * Crawler source configuration resource.
 * Toggle active, edit URL and crawl frequency.
 * Matches lostinhyd.sources schema.
 */
import {
  List,
  Datagrid,
  TextField,
  BooleanField,
  DateField,
  EditButton,
  Edit,
  SimpleForm,
  TextInput,
  SelectInput,
  BooleanInput,
} from "react-admin";

export function SourceList() {
  return (
    <List sort={{ field: "name", order: "ASC" }} pagination={false}>
      <Datagrid bulkActionButtons={false}>
        <TextField source="name" />
        <TextField source="url" />
        <TextField source="source_type" />
        <TextField source="crawl_frequency" />
        <BooleanField source="is_active" />
        <DateField source="last_crawled" showTime />
        <EditButton />
      </Datagrid>
    </List>
  );
}

export function SourceEdit() {
  return (
    <Edit>
      <SimpleForm>
        <TextInput source="name" disabled />
        <TextInput source="url" fullWidth />
        <TextInput source="source_type" disabled />
        <SelectInput
          source="crawl_frequency"
          choices={[
            { id: "hourly", name: "Hourly" },
            { id: "daily", name: "Daily" },
            { id: "weekly", name: "Weekly" },
          ]}
        />
        <BooleanInput source="is_active" />
      </SimpleForm>
    </Edit>
  );
}
