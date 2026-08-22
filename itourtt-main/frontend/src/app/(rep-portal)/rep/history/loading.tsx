import { ListPageSkeleton } from "@/components/ui/skeletons";

export default function Loading() {
  return <ListPageSkeleton rows={8} columns={4} filterCount={2} />;
}
