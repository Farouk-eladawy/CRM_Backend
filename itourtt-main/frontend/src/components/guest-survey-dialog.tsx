"use client";

import { useState, useEffect, useCallback } from "react";
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
import { Loader2, ClipboardList } from "lucide-react";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

interface GuestSurveyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  jobId: string;
  jobRef: string;
  portalApiBase: string;
  onSuccess: () => void;
}

const AGE_RANGES = ["20-30", "30-45", "45-60"];

interface SurveyForm {
  ageRange: string;
  noOfAdults: string;
  flightNo: string;
  noOfInfants: string;
  stayLength: string;
  repeaterGuest: string; // "YES" | "NO" | ""
  guestNationality: string;
  noOfChildren: string;
  localTravelAgent: string;
  hotelName: string;
  email: string;
  generalComment: string;
  contactNumber: string;
}

const EMPTY: SurveyForm = {
  ageRange: "",
  noOfAdults: "",
  flightNo: "",
  noOfInfants: "0",
  stayLength: "",
  repeaterGuest: "",
  guestNationality: "",
  noOfChildren: "0",
  localTravelAgent: "",
  hotelName: "",
  email: "",
  generalComment: "",
  contactNumber: "",
};

export function GuestSurveyDialog({
  open,
  onOpenChange,
  jobId,
  jobRef,
  portalApiBase,
  onSuccess,
}: GuestSurveyDialogProps) {
  const t = useT();
  const [form, setForm] = useState<SurveyForm>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isUpdate, setIsUpdate] = useState(false);

  const set = <K extends keyof SurveyForm>(k: K, v: SurveyForm[K]) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`${portalApiBase}/jobs/${jobId}/survey`);
      const { survey, prefill } = res.data?.data ?? res.data ?? {};
      if (survey) {
        setIsUpdate(true);
        setForm({
          ageRange: survey.ageRange ?? "",
          noOfAdults: String(survey.noOfAdults ?? ""),
          flightNo: survey.flightNo ?? "",
          noOfInfants: String(survey.noOfInfants ?? 0),
          stayLength: survey.stayLength ?? "",
          repeaterGuest: survey.repeaterGuest ?? "",
          guestNationality: survey.guestNationality ?? "",
          noOfChildren: String(survey.noOfChildren ?? 0),
          localTravelAgent: survey.localTravelAgent ?? "",
          hotelName: survey.hotelName ?? "",
          email: survey.email ?? "",
          generalComment: survey.generalComment ?? "",
          contactNumber: survey.contactNumber ?? "",
        });
      } else {
        setIsUpdate(false);
        setForm({
          ...EMPTY,
          flightNo: prefill?.flightNo ?? "",
          hotelName: prefill?.hotelName ?? "",
          noOfAdults: prefill?.paxCount != null ? String(prefill.paxCount) : "",
        });
      }
    } catch {
      setForm(EMPTY);
    } finally {
      setLoading(false);
    }
  }, [jobId, portalApiBase]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const canSubmit =
    !submitting &&
    !loading &&
    !!form.ageRange &&
    form.noOfAdults !== "" &&
    !!form.flightNo.trim() &&
    !!form.repeaterGuest &&
    !!form.guestNationality.trim() &&
    !!form.hotelName.trim() &&
    !!form.generalComment.trim() &&
    !!form.contactNumber.trim();

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await api.post(`${portalApiBase}/jobs/${jobId}/survey`, {
        ageRange: form.ageRange,
        noOfAdults: Number(form.noOfAdults) || 0,
        flightNo: form.flightNo.trim(),
        noOfInfants: Number(form.noOfInfants) || 0,
        stayLength: form.stayLength.trim() || undefined,
        repeaterGuest: form.repeaterGuest,
        guestNationality: form.guestNationality.trim(),
        noOfChildren: Number(form.noOfChildren) || 0,
        localTravelAgent: form.localTravelAgent.trim() || undefined,
        hotelName: form.hotelName.trim(),
        email: form.email.trim() || undefined,
        generalComment: form.generalComment.trim(),
        contactNumber: form.contactNumber.trim(),
      });
      toast.success(t("survey.success").replace("{ref}", jobRef));
      onOpenChange(false);
      onSuccess();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("survey.failed");
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const labelCls = "text-sm font-medium text-foreground";
  const inputCls =
    "mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
  const req = <span className="text-destructive">*</span>;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5" />
            {t("survey.title")}
          </DialogTitle>
          <DialogDescription>
            {t("survey.jobLabel")}{" "}
            <span className="font-semibold">{jobRef}</span>
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Age Range */}
            <div>
              <label className={labelCls}>{t("survey.ageRange")} {req}</label>
              <select
                className={inputCls}
                value={form.ageRange}
                onChange={(e) => set("ageRange", e.target.value)}
              >
                <option value="">—</option>
                {AGE_RANGES.map((r) => (
                  <option key={r} value={r}>
                    {r.replace("-", " – ")} {t("survey.years")}
                  </option>
                ))}
              </select>
            </div>

            {/* Repeater Guest */}
            <div>
              <label className={labelCls}>{t("survey.repeaterGuest")} {req}</label>
              <select
                className={inputCls}
                value={form.repeaterGuest}
                onChange={(e) => set("repeaterGuest", e.target.value)}
              >
                <option value="">—</option>
                <option value="YES">{t("survey.yes")}</option>
                <option value="NO">{t("survey.no")}</option>
              </select>
            </div>

            {/* No. of Adults */}
            <div>
              <label className={labelCls}>{t("survey.noOfAdults")} {req}</label>
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.noOfAdults}
                onChange={(e) => set("noOfAdults", e.target.value)}
              />
            </div>

            {/* No. of Children */}
            <div>
              <label className={labelCls}>{t("survey.noOfChildren")}</label>
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.noOfChildren}
                onChange={(e) => set("noOfChildren", e.target.value)}
              />
            </div>

            {/* No. of Infants */}
            <div>
              <label className={labelCls}>{t("survey.noOfInfants")}</label>
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.noOfInfants}
                onChange={(e) => set("noOfInfants", e.target.value)}
              />
            </div>

            {/* Flight No */}
            <div>
              <label className={labelCls}>{t("survey.flightNo")} {req}</label>
              <input
                className={inputCls}
                value={form.flightNo}
                onChange={(e) => set("flightNo", e.target.value)}
              />
            </div>

            {/* Guest Nationality */}
            <div>
              <label className={labelCls}>{t("survey.guestNationality")} {req}</label>
              <input
                className={inputCls}
                value={form.guestNationality}
                onChange={(e) => set("guestNationality", e.target.value)}
              />
            </div>

            {/* Hotel Name */}
            <div>
              <label className={labelCls}>{t("survey.hotelName")} {req}</label>
              <input
                className={inputCls}
                value={form.hotelName}
                onChange={(e) => set("hotelName", e.target.value)}
              />
            </div>

            {/* Stay Length */}
            <div>
              <label className={labelCls}>{t("survey.stayLength")}</label>
              <input
                className={inputCls}
                value={form.stayLength}
                onChange={(e) => set("stayLength", e.target.value)}
              />
            </div>

            {/* Local Travel Agent */}
            <div>
              <label className={labelCls}>{t("survey.localTravelAgent")}</label>
              <input
                className={inputCls}
                value={form.localTravelAgent}
                onChange={(e) => set("localTravelAgent", e.target.value)}
              />
            </div>

            {/* Email */}
            <div>
              <label className={labelCls}>{t("survey.email")}</label>
              <input
                type="email"
                className={inputCls}
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
              />
            </div>

            {/* Contact Number */}
            <div>
              <label className={labelCls}>{t("survey.contactNumber")} {req}</label>
              <input
                className={inputCls}
                value={form.contactNumber}
                onChange={(e) => set("contactNumber", e.target.value)}
              />
            </div>

            {/* General Comment (full width) */}
            <div className="sm:col-span-2">
              <label className={labelCls}>{t("survey.generalComment")} {req}</label>
              <textarea
                rows={3}
                className={inputCls}
                value={form.generalComment}
                onChange={(e) => set("generalComment", e.target.value)}
              />
            </div>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            {t("common.cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isUpdate ? t("survey.update") : t("survey.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
