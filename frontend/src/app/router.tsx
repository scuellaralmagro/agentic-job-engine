import { createBrowserRouter } from "react-router";
import { GlassPanel } from "@/components/GlassPanel";
import { Layout } from "./Layout";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { QueuePage } from "@/features/queue/QueuePage";
import { SearchPage } from "@/features/search/SearchPage";
import { RunDetailPage } from "@/features/search/RunDetailPage";
import { MatchDetailPage } from "@/features/offers/MatchDetailPage";
import { LibraryPage } from "@/features/library/LibraryPage";
import { ProjectionEditorPage } from "@/features/library/ProjectionEditorPage";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { SettingsPage } from "@/features/settings/SettingsPage";

function RouteError() {
  return (
    <GlassPanel className="m-8 text-center">
      <p className="font-medium text-danger">Something went wrong.</p>
      <p className="text-sm text-ink-dim">
        Try reloading, or check that the backend is running.
      </p>
    </GlassPanel>
  );
}

export const router = createBrowserRouter([
  {
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/search", element: <SearchPage /> },
      { path: "/search/runs/:id", element: <RunDetailPage /> },
      { path: "/queue", element: <QueuePage /> },
      { path: "/matches/:id", element: <MatchDetailPage /> },
      { path: "/library", element: <LibraryPage /> },
      { path: "/library/projections/:id", element: <ProjectionEditorPage /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/settings", element: <SettingsPage /> },
    ],
  },
]);
