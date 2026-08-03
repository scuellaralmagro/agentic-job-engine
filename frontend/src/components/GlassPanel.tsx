import { cn } from "@/lib/utils";

export function GlassPanel({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("glass p-5", className)} {...props} />;
}
