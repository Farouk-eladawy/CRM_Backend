import { PageHeaderSkeleton, FormSkeleton } from "@/components/ui/skeletons";

export default function Loading() {
  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeaderSkeleton hasButton={false} />
      <div className="rounded-xl border bg-card p-6">
        <FormSkeleton fields={8} />
      </div>
    </div>
  );
}
