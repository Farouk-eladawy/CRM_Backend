"use client";

import { useState, useRef } from "react";
import {
  Upload,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { LocationCombobox } from "@/components/location-combobox";
import api from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";
import { SELECTABLE_SERVICE_TYPES, serviceTypeDropdownLabel } from "@/lib/service-types";

interface Customer {
  id: string;
  legalName: string;
  tradeName: string | null;
}

interface ParsedJob {
  serviceType: string;
  jobDate: string;
  adultCount: number;
  childCount: number;
  originName: string;
  destinationName: string;
  originAirportId?: string;
  originZoneId?: string;
  originHotelId?: string;
  destinationAirportId?: string;
  destinationZoneId?: string;
  destinationHotelId?: string;
  customerJobId?: string;
  clientName?: string;
  flightNo?: string;
  arrivalTime?: string;
  departureTime?: string;
  pickUpTime?: string;
  notes?: string;
  confidence: number;
  warnings: string[];
  rowIndex: number;
}

interface ImportResult {
  created: number;
  errors: { index: number; message: string }[];
}

interface B2BJobImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customers: Customer[];
  onImportComplete: () => void;
}

const SERVICE_TYPES = SELECTABLE_SERVICE_TYPES;

type Step = "upload" | "review" | "result";

export function B2BJobImportModal({
  open,
  onOpenChange,
  customers,
  onImportComplete,
}: B2BJobImportModalProps) {
  const t = useT();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step state
  const [step, setStep] = useState<Step>("upload");

  // Upload step
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);

  // Review step
  const [parsedJobs, setParsedJobs] = useState<ParsedJob[]>([]);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [metadata, setMetadata] = useState<Record<string, unknown>>({});

  // Result step
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  function resetState() {
    setStep("upload");
    setSelectedCustomerId("");
    setSelectedFile(null);
    setExtracting(false);
    setParsedJobs([]);
    setSelectedRows(new Set());
    setMetadata({});
    setImporting(false);
    setImportResult(null);
  }

  function handleClose(isOpen: boolean) {
    if (!isOpen) {
      if (step === "review" && parsedJobs.length > 0) {
        if (!confirm("Discard extracted jobs?")) return;
      }
      resetState();
    }
    onOpenChange(isOpen);
  }

  async function handleExtract() {
    if (!selectedFile || !selectedCustomerId) return;

    setExtracting(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("customerId", selectedCustomerId);

      const res = await api.post("/ai-parser/extract-jobs", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000, // 5 min timeout for AI processing
      });

      const data = res.data.data;
      const jobs: ParsedJob[] = data.jobs || [];
      setMetadata(data.metadata || {});

      if (jobs.length === 0) {
        toast.error(t("jobImport.noJobsExtracted") || "No jobs could be extracted from this document");
        return;
      }

      setParsedJobs(jobs);
      // Select all high-confidence rows by default
      setSelectedRows(new Set(jobs.filter((j) => j.confidence >= 0.5).map((_, i) => i)));
      setStep("review");
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || "Failed to extract jobs";
      toast.error(msg);
    } finally {
      setExtracting(false);
    }
  }

  function updateJob(index: number, field: keyof ParsedJob, value: unknown) {
    setParsedJobs((prev) =>
      prev.map((j, i) => (i === index ? { ...j, [field]: value } : j)),
    );
  }

  function toggleRow(index: number) {
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function selectAll() {
    setSelectedRows(new Set(parsedJobs.map((_, i) => i)));
  }

  function deselectAll() {
    setSelectedRows(new Set());
  }

  async function handleImport() {
    const selectedJobs = parsedJobs.filter((_, i) => selectedRows.has(i));
    if (selectedJobs.length === 0) {
      toast.error("No jobs selected");
      return;
    }

    setImporting(true);
    try {
      // Map ParsedJob to CreateJobDto
      const jobs = selectedJobs.map((j) => ({
        bookingChannel: "B2B" as const,
        customerId: selectedCustomerId,
        serviceType: j.serviceType,
        jobDate: j.jobDate,
        adultCount: j.adultCount,
        childCount: j.childCount || 0,
        originAirportId: j.originAirportId || undefined,
        originZoneId: j.originZoneId || undefined,
        originHotelId: j.originHotelId || undefined,
        destinationAirportId: j.destinationAirportId || undefined,
        destinationZoneId: j.destinationZoneId || undefined,
        destinationHotelId: j.destinationHotelId || undefined,
        customerJobId: j.customerJobId || undefined,
        clientName: j.clientName || undefined,
        notes: j.notes || undefined,
        pickUpTime: j.pickUpTime ? `${j.jobDate}T${j.pickUpTime}:00` : undefined,
        flight: j.flightNo
          ? {
              flightNo: j.flightNo,
              // Only the flight time matching the service type is persisted so a
              // stale arrival/departure value can't leak onto the wrong job type.
              arrivalTime:
                j.serviceType === "ARR" && j.arrivalTime ? `${j.jobDate}T${j.arrivalTime}:00` : undefined,
              departureTime:
                j.serviceType === "DEP" && j.departureTime ? `${j.jobDate}T${j.departureTime}:00` : undefined,
            }
          : undefined,
      }));

      const res = await api.post("/traffic-jobs/bulk", { jobs });
      const result: ImportResult = res.data.data;
      setImportResult(result);
      setStep("result");

      if (result.errors.length === 0) {
        toast.success(
          (t("jobImport.importSuccess") || "Successfully imported {count} jobs").replace(
            "{count}",
            String(result.created),
          ),
        );
      } else {
        toast.warning(
          `Imported ${result.created} of ${jobs.length} jobs (${result.errors.length} failures)`,
        );
      }
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Failed to import jobs");
    } finally {
      setImporting(false);
    }
  }

  function handleDone() {
    resetState();
    onOpenChange(false);
    onImportComplete();
  }

  const customerName = customers.find((c) => c.id === selectedCustomerId);
  const lowConfidenceCount = parsedJobs.filter((j) => j.confidence < 0.5).length;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-6xl max-h-[90vh] overflow-y-auto border-border bg-card text-foreground">
        <DialogHeader>
          <DialogTitle>
            {step === "upload" && (t("jobImport.title") || "Import Jobs from File")}
            {step === "review" && (t("jobImport.reviewTitle") || "Review Extracted Jobs")}
            {step === "result" && "Import Results"}
          </DialogTitle>
          {step === "review" && (
            <DialogDescription>
              {t("jobImport.reviewDescription") || "Review and correct the extracted jobs before importing"}
            </DialogDescription>
          )}
        </DialogHeader>

        {/* ─── Step 1: Upload ─── */}
        {step === "upload" && (
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t("jobImport.selectCustomer") || "Select Customer"}</Label>
              <Select value={selectedCustomerId} onValueChange={setSelectedCustomerId}>
                <SelectTrigger className="border-border bg-card text-foreground">
                  <SelectValue placeholder="Select customer..." />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground max-h-60">
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.tradeName || c.legalName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t("jobImport.uploadFile") || "Upload File"}</Label>
              <Input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="border-border bg-card text-foreground"
              />
              <p className="text-xs text-muted-foreground">
                Accepted: PDF, Excel (.xlsx, .xls), Images (.png, .jpg). Max 10MB.
              </p>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => handleClose(false)} className="border-border">
                Cancel
              </Button>
              <Button
                onClick={handleExtract}
                disabled={!selectedFile || !selectedCustomerId || extracting}
                className="gap-1.5"
              >
                {extracting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("jobImport.extracting") || "Analyzing document with AI..."}
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4" />
                    Extract Jobs
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* ─── Step 2: Review ─── */}
        {step === "review" && (
          <div className="space-y-3">
            {/* Summary bar */}
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                {parsedJobs.length} jobs extracted from{" "}
                <span className="text-foreground font-medium">{String(metadata.fileName || "")}</span>
                {customerName && (
                  <>
                    {" "}for{" "}
                    <span className="text-foreground font-medium">
                      {customerName.tradeName || customerName.legalName}
                    </span>
                  </>
                )}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={selectAll} className="border-border text-xs">
                  Select All
                </Button>
                <Button variant="outline" size="sm" onClick={deselectAll} className="border-border text-xs">
                  Deselect All
                </Button>
              </div>
            </div>

            {/* Low confidence warning */}
            {lowConfidenceCount > 0 && (
              <div className="flex items-center gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-600 dark:text-yellow-400">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                {(t("jobImport.lowConfidenceWarning") || "{count} rows have low confidence and may need manual correction").replace(
                  "{count}",
                  String(lowConfidenceCount),
                )}
              </div>
            )}

            {/* Jobs table */}
            <div className="rounded-md border border-border overflow-x-auto max-h-[50vh] overflow-y-auto">
              <Table>
                <TableHeader className="sticky top-0 z-10">
                  <TableRow className="bg-muted">
                    <TableHead className="text-gray-200 w-10"></TableHead>
                    <TableHead className="text-gray-200 w-8">#</TableHead>
                    <TableHead className="text-gray-200">Type</TableHead>
                    <TableHead className="text-gray-200">Date</TableHead>
                    <TableHead className="text-gray-200 w-14">Pax</TableHead>
                    <TableHead className="text-gray-200">Origin</TableHead>
                    <TableHead className="text-gray-200">Destination</TableHead>
                    <TableHead className="text-gray-200">Client</TableHead>
                    <TableHead className="text-gray-200">Flight</TableHead>
                    <TableHead className="text-gray-200">Time</TableHead>
                    <TableHead className="text-gray-200 w-16">Conf.</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {parsedJobs.map((job, idx) => {
                    const isSelected = selectedRows.has(idx);
                    const bgClass =
                      job.confidence >= 0.8
                        ? "bg-emerald-500/5"
                        : job.confidence >= 0.5
                          ? "bg-yellow-500/5"
                          : "bg-red-500/5";

                    return (
                      <TableRow
                        key={idx}
                        className={`border-border ${bgClass} ${!isSelected ? "opacity-50" : ""}`}
                      >
                        <TableCell>
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={() => toggleRow(idx)}
                          />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {idx + 1}
                        </TableCell>
                        <TableCell>
                          <Select
                            value={job.serviceType}
                            onValueChange={(v) => updateJob(idx, "serviceType", v)}
                          >
                            <SelectTrigger className="h-7 w-24 text-xs border-border bg-transparent">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="border-border bg-popover text-foreground">
                              {SERVICE_TYPES.map((st) => (
                                <SelectItem key={st} value={st} className="text-xs">
                                  {serviceTypeDropdownLabel(st)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Input
                            type="date"
                            value={job.jobDate}
                            onChange={(e) => updateJob(idx, "jobDate", e.target.value)}
                            min="2020-01-01"
                            className="h-7 w-32 text-xs border-border bg-transparent"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            value={job.adultCount}
                            onChange={(e) => updateJob(idx, "adultCount", parseInt(e.target.value) || 1)}
                            className="h-7 w-14 text-xs border-border bg-transparent"
                            min={1}
                          />
                        </TableCell>
                        <TableCell className="min-w-[180px]">
                          <LocationCombobox
                            value={job.originAirportId || job.originZoneId || job.originHotelId || ""}
                            onChange={(id, type) => {
                              // Clear previous origin fields
                              const updates: Partial<ParsedJob> = {
                                originAirportId: undefined,
                                originZoneId: undefined,
                                originHotelId: undefined,
                              };
                              if (type === "AIRPORT") updates.originAirportId = id;
                              else if (type === "ZONE") updates.originZoneId = id;
                              else if (type === "HOTEL") updates.originHotelId = id;
                              setParsedJobs((prev) =>
                                prev.map((j, i) => (i === idx ? { ...j, ...updates } : j)),
                              );
                            }}
                            placeholder={job.originName || "Origin..."}
                          />
                        </TableCell>
                        <TableCell className="min-w-[180px]">
                          <LocationCombobox
                            value={job.destinationAirportId || job.destinationZoneId || job.destinationHotelId || ""}
                            onChange={(id, type) => {
                              const updates: Partial<ParsedJob> = {
                                destinationAirportId: undefined,
                                destinationZoneId: undefined,
                                destinationHotelId: undefined,
                              };
                              if (type === "AIRPORT") updates.destinationAirportId = id;
                              else if (type === "ZONE") updates.destinationZoneId = id;
                              else if (type === "HOTEL") updates.destinationHotelId = id;
                              setParsedJobs((prev) =>
                                prev.map((j, i) => (i === idx ? { ...j, ...updates } : j)),
                              );
                            }}
                            placeholder={job.destinationName || "Destination..."}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={job.clientName || ""}
                            onChange={(e) => updateJob(idx, "clientName", e.target.value)}
                            className="h-7 w-28 text-xs border-border bg-transparent"
                            placeholder="Client"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={job.flightNo || ""}
                            onChange={(e) => updateJob(idx, "flightNo", e.target.value)}
                            className="h-7 w-20 text-xs border-border bg-transparent"
                            placeholder="Flight"
                          />
                        </TableCell>
                        <TableCell>
                          {(() => {
                            // Bind the cell to the single time field that matches the
                            // service type so it neither displays nor writes a stale
                            // value into the wrong field (e.g. arrival time on a DEP job).
                            const field =
                              job.serviceType === "ARR"
                                ? "arrivalTime"
                                : job.serviceType === "DEP"
                                  ? "departureTime"
                                  : "pickUpTime";
                            return (
                              <Input
                                value={job[field] || ""}
                                onChange={(e) => updateJob(idx, field, e.target.value)}
                                className="h-7 w-20 text-xs border-border bg-transparent"
                                placeholder="HH:MM"
                              />
                            );
                          })()}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`text-xs ${
                              job.confidence >= 0.8
                                ? "border-emerald-500/30 text-emerald-600"
                                : job.confidence >= 0.5
                                  ? "border-yellow-500/30 text-yellow-600"
                                  : "border-red-500/30 text-red-600"
                            }`}
                            title={job.warnings.join("\n")}
                          >
                            {Math.round(job.confidence * 100)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setStep("upload")} className="border-border">
                Back
              </Button>
              <Button
                onClick={handleImport}
                disabled={selectedRows.size === 0 || importing}
                className="gap-1.5"
              >
                {importing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("jobImport.importing") || "Importing jobs..."}
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    {t("jobImport.importSelected") || "Import Selected"} ({selectedRows.size})
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* ─── Step 3: Result ─── */}
        {step === "result" && importResult && (
          <div className="space-y-4 py-2">
            <div className="flex flex-col items-center gap-3 py-6">
              {importResult.errors.length === 0 ? (
                <CheckCircle2 className="h-12 w-12 text-emerald-500" />
              ) : (
                <AlertTriangle className="h-12 w-12 text-yellow-500" />
              )}
              <p className="text-lg font-medium text-foreground">
                {importResult.created} jobs imported successfully
              </p>
              {importResult.errors.length > 0 && (
                <p className="text-sm text-muted-foreground">
                  {importResult.errors.length} jobs failed
                </p>
              )}
            </div>

            {importResult.errors.length > 0 && (
              <div className="rounded-md border border-red-500/30 overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-red-500/10">
                      <TableHead className="text-red-600">Row</TableHead>
                      <TableHead className="text-red-600">Error</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {importResult.errors.map((err, i) => (
                      <TableRow key={i} className="border-red-500/20">
                        <TableCell className="text-sm">{err.index + 1}</TableCell>
                        <TableCell className="text-sm text-red-500">{err.message}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            <DialogFooter>
              <Button onClick={handleDone} className="gap-1.5">
                <CheckCircle2 className="h-4 w-4" />
                Done
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
