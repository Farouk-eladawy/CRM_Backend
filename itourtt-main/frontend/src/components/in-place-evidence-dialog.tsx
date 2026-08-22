"use client";

import { useState, useEffect, useRef } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Loader2, Camera, MapPin, AlertCircle, X } from "lucide-react";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";
import { useGeoCapture } from "@/lib/use-geo-capture";

const REQUIRED_IMAGES = 2;


interface InPlaceEvidenceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  jobId: string;
  jobRef: string;
  portalApiBase: string;
  onSuccess: () => void;
}

interface ImageSlot {
  file: File;
  preview: string;
}

export function InPlaceEvidenceDialog({
  open,
  onOpenChange,
  jobId,
  jobRef,
  portalApiBase,
  onSuccess,
}: InPlaceEvidenceDialogProps) {
  const t = useT();
  const [images, setImages] = useState<ImageSlot[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { gps, gpsError, gpsLoading, retry } = useGeoCapture(open);

  // Reset selected images whenever the dialog closes.
  useEffect(() => {
    if (!open) setImages([]);
  }, [open]);

  const handleFilesSelected = (files: FileList | null) => {
    if (!files) return;
    const remaining = REQUIRED_IMAGES - images.length;
    const newFiles = Array.from(files).slice(0, remaining);
    for (const file of newFiles) {
      const preview = URL.createObjectURL(file);
      setImages((prev) => {
        if (prev.length >= REQUIRED_IMAGES) return prev;
        return [...prev, { file, preview }];
      });
    }
  };

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  const canSubmit = images.length === REQUIRED_IMAGES && !submitting && !!gps;

  const handleSubmit = async () => {
    if (images.length < REQUIRED_IMAGES) return;

    setSubmitting(true);
    try {
      const formData = new FormData();
      images.forEach((img) => formData.append("images", img.file));
      if (gps) {
        formData.append("latitude", gps.lat.toString());
        formData.append("longitude", gps.lng.toString());
      }

      await api.post(`${portalApiBase}/jobs/${jobId}/in-place`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast.success(t("inPlace.success").replace("{ref}", jobRef));
      onOpenChange(false);
      onSuccess();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("inPlace.failedSubmit");
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t("inPlace.title")}</DialogTitle>
          <DialogDescription>
            {t("inPlace.markJob")} <span className="font-semibold">{jobRef}</span> {t("inPlace.asInPlace")}{" "}
            {t("inPlace.uploadPhotos")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Images */}
          <div>
            <label className="text-sm font-medium text-foreground">
              {t("inPlace.photos")} ({images.length}/{REQUIRED_IMAGES})
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              multiple
              className="hidden"
              onChange={(e) => {
                handleFilesSelected(e.target.files);
                e.target.value = "";
              }}
            />

            <div className="mt-1 grid grid-cols-2 gap-2">
              {images.map((img, i) => (
                <div key={i} className="relative h-32 rounded-lg overflow-hidden border border-border">
                  <img
                    src={img.preview}
                    alt={`Evidence ${i + 1}`}
                    className="h-full w-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(i)}
                    className="absolute top-1 right-1 rounded-full bg-black/60 p-0.5 text-white hover:bg-black/80"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}

              {images.length < REQUIRED_IMAGES && (
                <div
                  className="flex h-32 cursor-pointer items-center justify-center rounded-lg border-2 border-dashed border-border bg-muted/30 transition-colors hover:border-primary/50"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="flex flex-col items-center gap-1 text-muted-foreground">
                    <Camera className="h-5 w-5" />
                    <span className="text-[10px]">{t("inPlace.tapToTakePhoto")}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* GPS Location */}
          <div>
            <label className="text-sm font-medium text-foreground">
              {t("noShow.gpsLocation")}
            </label>
            <div className="mt-1 flex items-center gap-2 rounded-lg border border-border bg-muted/30 p-3">
              {gpsLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    {t("noShow.capturingLocation")}
                  </span>
                </>
              ) : gpsError ? (
                <div className="flex flex-1 flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
                    <span className="text-sm text-destructive">{gpsError}</span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={retry}
                      className="ml-auto h-7 px-2 text-xs"
                    >
                      {t("noShow.retryLocation")}
                    </Button>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {t("noShow.locationRequired")}
                  </span>
                </div>
              ) : gps ? (
                <>
                  <MapPin className="h-4 w-4 text-green-500" />
                  <div className="flex-1">
                    <p className="text-sm text-foreground">
                      {gps.lat.toFixed(6)}, {gps.lng.toFixed(6)}
                    </p>
                    <a
                      href={`https://www.google.com/maps?q=${gps.lat},${gps.lng}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline"
                    >
                      {t("noShow.viewOnMaps")}
                    </a>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("inPlace.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
