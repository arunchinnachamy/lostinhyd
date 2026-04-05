/**
 * Main React Admin application.
 * Defines resources for events, venues, sources, and crawl logs.
 */
import { Admin, Resource } from "react-admin";
import { dataProvider } from "./dataProvider";
import { authProvider } from "./authProvider";
import { Dashboard } from "./pages/Dashboard";
import { EventList, EventEdit } from "./resources/events";
import { VenueList, VenueEdit } from "./resources/venues";
import { SourceList, SourceEdit } from "./resources/sources";
import { CrawlLogList } from "./resources/crawlLogs";

export function App() {
  return (
    <Admin
      dataProvider={dataProvider}
      authProvider={authProvider}
      dashboard={Dashboard}
      title="Lost in Hyd - Control Centre"
    >
      <Resource
        name="events"
        list={EventList}
        edit={EventEdit}
        options={{ label: "Events" }}
      />
      <Resource
        name="venues"
        list={VenueList}
        edit={VenueEdit}
        options={{ label: "Venues" }}
      />
      <Resource
        name="sources"
        list={SourceList}
        edit={SourceEdit}
        options={{ label: "Crawler Sources" }}
      />
      <Resource
        name="crawl-logs"
        list={CrawlLogList}
        options={{ label: "Crawl Logs" }}
      />
    </Admin>
  );
}
