import { ListPageSkeleton } from "@/components/ui/skeletons";

export default function Loading() {
  return <ListPageSkeleton rows={12} columns={5} filterCount={2} />;
}
