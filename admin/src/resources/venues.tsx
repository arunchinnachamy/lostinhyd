/**
 * Venue resource: list and edit form.
 * Matches lostinhyd.venues schema.
 */
import {
  List,
  Datagrid,
  TextField,
  DateField,
  EditButton,
  Edit,
  SimpleForm,
  TextInput,
  NumberInput,
  TopToolbar,
  FilterButton,
} from "react-admin";

const venueFilters = [
  <TextInput key="q" source="q" label="Search" alwaysOn />,
  <TextInput key="area" source="area" />,
];

const VenueListActions = () => (
  <TopToolbar>
    <FilterButton />
  </TopToolbar>
);

export function VenueList() {
  return (
    <List
      filters={venueFilters}
      actions={<VenueListActions />}
      sort={{ field: "created_at", order: "DESC" }}
    >
      <Datagrid>
        <TextField source="name" />
        <TextField source="area" />
        <TextField source="city" />
        <TextField source="phone" />
        <TextField source="website" />
        <DateField source="created_at" showTime />
        <EditButton />
      </Datagrid>
    </List>
  );
}

export function VenueEdit() {
  return (
    <Edit>
      <SimpleForm>
        <TextInput source="name" fullWidth />
        <TextInput source="address" multiline fullWidth rows={2} />
        <TextInput source="city" defaultValue="Hyderabad" />
        <TextInput source="area" />
        <TextInput source="state" defaultValue="Telangana" />
        <TextInput source="country" defaultValue="India" />
        <TextInput source="pincode" />
        <NumberInput source="latitude" />
        <NumberInput source="longitude" />
        <TextInput source="phone" />
        <TextInput source="website" fullWidth />
        <TextInput source="google_maps_url" fullWidth />
      </SimpleForm>
    </Edit>
  );
}
