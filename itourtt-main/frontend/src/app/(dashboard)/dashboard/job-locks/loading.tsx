import { ListPageSkeleton } from "@/components/ui/skeletons";

export default function Loading() {
  return <ListPageSkeleton rows={6} columns={4} filterCount={2} />;
}
