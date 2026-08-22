import { type LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  heading: string;
  description: string;
}

export function EmptyState({ icon: Icon, heading, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 text-center">
      <Icon className="h-12 w-12 text-muted-foreground/30" />
      <p className="text-sm font-semibold text-foreground">{heading}</p>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}
