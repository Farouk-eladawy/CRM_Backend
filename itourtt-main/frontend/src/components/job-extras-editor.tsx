"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import api from "@/lib/api";

const CURRENCIES = ["EGP", "USD", "EUR", "GBP", "SAR"];

export interface JobExtra {
  id?: string;
  extraId: string | null;
  name: string;
  qty: number;
  unitAmount: number;
  currency: string;
  source: "B2C" | "MANUAL";
}

interface CatalogExtra {
  id: string;
  name: string;
  price: number;
  currency: string;
}

interface JobExtrasEditorProps {
  value: JobExtra[];
  onChange: (extras: JobExtra[]) => void;
  disabled?: boolean;
}

// Editor for a job's managed extras. Catalog items default name/amount/currency,
// but every field stays operator-overridable (for offline / manual data entry).
export function JobExtrasEditor({ value, onChange, disabled }: JobExtrasEditorProps) {
  const [catalog, setCatalog] = useState<CatalogExtra[]>([]);

  useEffect(() => {
    let active = true;
    api
      .get("/extras/selectable")
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.data || [];
        if (active) setCatalog(list);
      })
      .catch(() => {
        if (active) setCatalog([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const update = (idx: number, patch: Partial<JobExtra>) => {
    onChange(value.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  };

  const remove = (idx: number) => {
    onChange(value.filter((_, i) => i !== idx));
  };

  const addRow = () => {
    onChange([
      ...value,
      { extraId: null, name: "", qty: 1, unitAmount: 0, currency: "EGP", source: "MANUAL" },
    ]);
  };

  const onPickCatalog = (idx: number, extraId: string) => {
    const ex = catalog.find((c) => c.id === extraId);
    if (!ex) {
      update(idx, { extraId: null });
      return;
    }
    update(idx, {
      extraId: ex.id,
      name: ex.name,
      unitAmount: Number(ex.price),
      currency: ex.currency,
    });
  };

  // Per-currency subtotals (qty * unitAmount), grouped by currency.
  const subtotals = value.reduce<Record<string, number>>((acc, row) => {
    const amt = (Number(row.qty) || 0) * (Number(row.unitAmount) || 0);
    acc[row.currency] = (acc[row.currency] || 0) + amt;
    return acc;
  }, {});

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="space-y-2">
          {value.map((row, idx) => (
            <div key={row.id ?? idx} className="grid grid-cols-[2fr_4rem_6rem_5rem_auto] items-center gap-2">
              <div className="flex items-center gap-1.5 min-w-0">
                <Select
                  value={row.extraId ?? "__custom__"}
                  onValueChange={(v) => onPickCatalog(idx, v)}
                  disabled={disabled}
                >
                  <SelectTrigger className="border-border bg-card text-foreground h-8 min-w-0">
                    <SelectValue placeholder="Select extra">
                      {row.name || "Select extra"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {catalog.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name} ({Number(c.price).toLocaleString()} {c.currency})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {row.source === "B2C" && (
                  <Badge variant="secondary" className="shrink-0 text-[10px]">Website</Badge>
                )}
              </div>
              <Input
                type="number"
                min="1"
                value={row.qty}
                onChange={(e) => update(idx, { qty: parseInt(e.target.value) || 1 })}
                disabled={disabled}
                className="border-border bg-card text-foreground h-8 text-center"
              />
              <Input
                type="number"
                min="0"
                step="0.01"
                value={row.unitAmount}
                onChange={(e) => update(idx, { unitAmount: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="border-border bg-card text-foreground h-8 text-right"
              />
              <Select
                value={row.currency}
                onValueChange={(v) => update(idx, { currency: v })}
                disabled={disabled}
              >
                <SelectTrigger className="border-border bg-card text-foreground h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => remove(idx)}
                disabled={disabled}
                className="h-8 w-8 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {Object.entries(subtotals).map(([cur, amt]) => (
              <span key={cur}>
                {amt.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {cur}
              </span>
            ))}
          </div>
        </div>
      )}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={addRow}
        disabled={disabled}
        className="h-8"
      >
        <Plus className="h-4 w-4 mr-1" /> Add Extra
      </Button>
    </div>
  );
}
