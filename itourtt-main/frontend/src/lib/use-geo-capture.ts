"use client";

import { useCallback, useEffect, useState } from "react";
import { captureGPS, type GeoError } from "@/lib/gps";
import { useT } from "@/lib/i18n";

export interface GeoCapture {
  gps: { lat: number; lng: number } | null;
  gpsError: string | null;
  gpsLoading: boolean;
  /** Re-attempt the location capture (e.g. from a "Retry" button). */
  retry: () => void;
}

/**
 * Captures the device location for evidence dialogs.
 *
 * Uses the staged high-accuracy → network fallback in `captureGPS`. A fix is
 * mandatory: capture failures are surfaced via `gpsError` with a Retry button,
 * and dialogs keep the submit button disabled until coordinates are obtained.
 *
 * @param active capture only while truthy (typically the dialog `open` flag);
 *   resets state when it becomes false.
 */
export function useGeoCapture(active: boolean): GeoCapture {
  const t = useT();
  const [gps, setGps] = useState<{ lat: number; lng: number } | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);

  const capture = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setGpsError(t("noShow.geoNotSupported"));
      setGpsLoading(false);
      return;
    }
    setGpsLoading(true);
    setGpsError(null);
    captureGPS()
      .then((coords) => {
        setGps(coords);
        setGpsError(null);
      })
      .catch((err: GeoError) => {
        switch (err?.code) {
          case 1:
            setGpsError(t("noShow.permissionDenied"));
            break;
          case 2:
            setGpsError(t("noShow.locationUnavailable"));
            break;
          case 3:
            setGpsError(t("noShow.locationTimeout"));
            break;
          default:
            setGpsError(t("noShow.failedLocation"));
        }
      })
      .finally(() => setGpsLoading(false));
  }, [t]);

  useEffect(() => {
    if (!active) {
      setGps(null);
      setGpsError(null);
      setGpsLoading(false);
      return;
    }
    capture();
  }, [active, capture]);

  return { gps, gpsError, gpsLoading, retry: capture };
}
