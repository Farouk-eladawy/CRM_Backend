import { PageHeaderSkeleton, TableSkeleton } from "@/components/ui/skeletons";

export default function Loading() {
  return (
    <div className="space-y-5">
      <PageHeaderSkeleton hasButton={false} />
      <TableSkeleton rows={10} columns={5} />
    </div>
  );
}
