import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassPanel } from "@/components/GlassPanel";
import { useRebuildEmbeddings } from "./queries";
import pkg from "../../../package.json";

export function SettingsPage() {
  const rebuild = useRebuildEmbeddings();

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Settings</h1>

      <GlassPanel className="flex items-center gap-4">
        <div className="mr-auto">
          <h2 className="font-medium">System</h2>
          <p className="text-xs text-ink-dim">aje-frontend v{pkg.version}</p>
        </div>
        <Button
          variant="secondary"
          disabled={rebuild.isPending}
          onClick={() => rebuild.mutate()}
        >
          <RefreshCw className="size-3.5" />
          {rebuild.isPending ? "Rebuilding…" : "Rebuild embeddings"}
        </Button>
      </GlassPanel>

      <p className="text-sm text-ink-dim">
        Saved searches and offer import moved to the Search tab.
      </p>
    </div>
  );
}
