import { FileDown, FolderOpen, Pencil, Trash2 } from "lucide-react";
import { Link } from "react-router";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/EmptyState";
import { GlassPanel } from "@/components/GlassPanel";
import {
  useDeleteProjection,
  useProjections,
  useRenderProjection,
} from "./queries";

export function LibraryPage() {
  const projections = useProjections();
  const del = useDeleteProjection();
  const render = useRenderProjection();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Library</h1>
      <Tabs defaultValue="projections" className="space-y-4">
        <TabsList>
          <TabsTrigger value="projections">Tailored CVs</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>
        <TabsContent value="projections">
          {(projections.data ?? []).length === 0 ? (
            <GlassPanel>
              <EmptyState
                icon={FolderOpen}
                title="No tailored CVs yet"
                hint='Accept an offer and hit "Adapt CV" on its detail page.'
              />
            </GlassPanel>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {projections.data!.map((p) => (
                <GlassPanel key={p.id} className="flex flex-col gap-2">
                  <p className="font-medium">{p.name}</p>
                  <p className="text-xs text-ink-dim">
                    {p.content_json.headline} ·{" "}
                    {new Date(p.created_at).toLocaleDateString()}
                  </p>
                  <div className="mt-auto flex flex-wrap gap-1.5 pt-2">
                    <Button asChild size="sm" variant="secondary">
                      <Link to={`/library/projections/${p.id}`}>
                        <Pencil className="size-3.5" /> Edit
                      </Link>
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={render.isPending}
                      onClick={() => render.mutate(p.id)}
                    >
                      <FileDown className="size-3.5" /> Render
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-danger"
                        >
                          <Trash2 className="size-3.5" /> Delete
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent className="glass-elevated">
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            Delete "{p.name}"?
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            This removes the tailored CV. Rendered PDFs stay in
                            Documents.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => del.mutate(p.id)}>
                            Confirm
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </GlassPanel>
              ))}
            </div>
          )}
        </TabsContent>
        <TabsContent value="documents">
          <div data-testid="documents-tab" />
        </TabsContent>
      </Tabs>
    </div>
  );
}
