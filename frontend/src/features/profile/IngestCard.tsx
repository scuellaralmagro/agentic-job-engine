import { useRef, useState } from "react";
import { Loader2, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIngest } from "./queries";

export function IngestCard() {
  const ingest = useIngest();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const upload = (file: File | undefined) => {
    if (file) ingest.mutate(file);
  };

  return (
    <div
      className={cn(
        "flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-line bg-surface px-4 py-3 text-sm transition-colors",
        dragging && "border-brand bg-brand/5",
      )}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        upload(e.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        aria-label="Upload CV or LinkedIn export"
        type="file"
        accept=".pdf,.docx,.zip"
        // sr-only rather than hidden: a display:none input is unreachable by keyboard.
        className="sr-only"
        onChange={(e) => upload(e.target.files?.[0])}
      />
      {ingest.isPending ? (
        <>
          <Loader2 className="size-4 animate-spin text-brand" />
          Extracting — this can take a minute…
        </>
      ) : (
        <>
          <Upload className="size-4 text-brand" />
          Ingest CV (PDF/DOCX) or LinkedIn export (ZIP)
        </>
      )}
    </div>
  );
}
