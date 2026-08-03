import { useQuery } from "@tanstack/react-query";
import {
  Inbox,
  LayoutDashboard,
  Library,
  Search,
  Settings,
  User,
} from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { apiFetch } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/search", label: "Search", icon: Search },
  { to: "/queue", label: "Queue", icon: Inbox },
  { to: "/library", label: "Library", icon: Library },
  { to: "/profile", label: "Profile", icon: User },
  { to: "/settings", label: "Settings", icon: Settings },
];

function HealthDot() {
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<{ status: string }>("/health"),
    refetchInterval: 30_000,
    retry: false,
  });
  const ok = !isError && data?.status === "ok";
  return (
    <div className="flex items-center gap-2 text-xs text-ink-dim">
      <span
        data-testid="health-dot"
        data-status={ok ? "ok" : "down"}
        className={cn(
          "size-2 rounded-full",
          ok ? "bg-ok" : "bg-danger animate-pulse",
        )}
      />
      {ok ? "Backend online" : "Backend unreachable"}
    </div>
  );
}

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="glass sticky top-3 m-3 flex h-[calc(100vh-1.5rem)] w-56 shrink-0 flex-col p-4">
        <p className="px-2 pb-4 text-sm font-semibold tracking-wide text-brand">
          AJE
        </p>
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink-dim transition-colors hover:bg-white/5 hover:text-ink",
                  isActive && "bg-brand/15 text-brand",
                )
              }
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <HealthDot />
      </aside>
      <main className="min-w-0 flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
