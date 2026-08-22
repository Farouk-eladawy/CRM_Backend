"use client";

import { useState, useCallback } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import type { PermissionNode, CrudType } from "@/lib/permission-registry";
import { PERMISSION_REGISTRY, getDescendantKeys, getAncestorKeys } from "@/lib/permission-registry";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PermissionMatrixProps {
  granted: Set<string>;
  onChange: (next: Set<string>) => void;
  disabled?: boolean;
}

// CRUD group display config
const CRUD_GROUPS: { type: CrudType; label: string; color: string }[] = [
  { type: 'C',      label: 'Create',  color: 'text-emerald-500' },
  { type: 'R',      label: 'Read',    color: 'text-blue-400' },
  { type: 'U',      label: 'Update',  color: 'text-amber-400' },
  { type: 'D',      label: 'Delete',  color: 'text-red-400' },
  { type: 'export', label: 'Export',  color: 'text-purple-400' },
  { type: 'import', label: 'Import',  color: 'text-cyan-400' },
  { type: 'action', label: 'Actions', color: 'text-orange-400' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Collect all leaf/non-section descendant nodes of given type from a node list */
function collectByType(nodes: PermissionNode[], types: CrudType[]): PermissionNode[] {
  const result: PermissionNode[] = [];
  for (const node of nodes) {
    if (node.crudType && types.includes(node.crudType)) {
      result.push(node);
    }
    if (node.children) {
      result.push(...collectByType(node.children, types));
    }
  }
  return result;
}

/** Collect all section-typed children (direct only) */
function directSections(nodes: PermissionNode[]): PermissionNode[] {
  return nodes.filter((n) => n.crudType === 'section');
}

/** All field nodes deep inside a node's children */
function collectFields(nodes: PermissionNode[]): PermissionNode[] {
  return collectByType(nodes, ['field']);
}

/** Count how many descendants of a key are granted */
function countGranted(key: string, granted: Set<string>): { on: number; total: number } {
  const desc = getDescendantKeys(key);
  return { on: desc.filter((k) => granted.has(k)).length, total: desc.length };
}

// ─── Main component ───────────────────────────────────────────────────────────

export function PermissionMatrix({ granted, onChange, disabled = false }: PermissionMatrixProps) {
  // Only render top-level 'page' nodes
  const pages = PERMISSION_REGISTRY.filter((n) => n.crudType === 'page');

  const toggle = useCallback(
    (key: string, on: boolean) => {
      if (disabled) return;
      const next = new Set(granted);
      if (on) {
        next.add(key);
        for (const a of getAncestorKeys(key)) next.add(a);
        for (const d of getDescendantKeys(key)) next.add(d);
      } else {
        next.delete(key);
        for (const d of getDescendantKeys(key)) next.delete(d);
      }
      onChange(next);
    },
    [granted, onChange, disabled],
  );

  return (
    <div className="space-y-2">
      {pages.map((page) => (
        <PageSection
          key={page.key}
          node={page}
          granted={granted}
          toggle={toggle}
          disabled={disabled}
        />
      ))}
    </div>
  );
}

// ─── Page section card ────────────────────────────────────────────────────────

interface PageSectionProps {
  node: PermissionNode;
  granted: Set<string>;
  toggle: (key: string, on: boolean) => void;
  disabled: boolean;
}

function PageSection({ node, granted, toggle, disabled }: PageSectionProps) {
  const t = useT();
  const isOn = granted.has(node.key);
  const [expanded, setExpanded] = useState(false);
  const { on, total } = countGranted(node.key, granted);

  const label = resolveLabel(t, node);
  const children = node.children ?? [];

  // Gather CRUD rows: direct-child non-section nodes + flattened from sections
  const crudNodes = collectByType(children, ['C', 'R', 'U', 'D', 'export', 'import', 'action']);
  // Sub-sections (for field-level and action sub-groups)
  const subSections = directSections(children).filter((s) => {
    const fields = collectFields(s.children ?? []);
    return fields.length > 0 || (s.children ?? []).some((c) => c.crudType === 'action');
  });

  return (
    <div
      className={cn(
        "rounded-lg border transition-colors",
        isOn
          ? "border-border bg-card"
          : "border-border/50 bg-muted/20",
      )}
    >
      {/* ── Section header ── */}
      <div className="flex items-center gap-3 px-4 py-3">
        <Switch
          checked={isOn}
          disabled={disabled}
          onCheckedChange={(on) => toggle(node.key, on)}
          className="shrink-0"
        />
        <span
          className={cn(
            "flex-1 text-sm font-semibold select-none",
            isOn ? "text-foreground" : "text-muted-foreground",
          )}
        >
          {label}
        </span>

        {isOn && total > 0 && (
          <span className="text-[10px] tabular-nums text-muted-foreground/60">
            {on}/{total}
          </span>
        )}

        {isOn && (crudNodes.length > 0 || subSections.length > 0) && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="ml-1 rounded p-0.5 hover:bg-muted"
          >
            {expanded
              ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
          </button>
        )}
      </div>

      {/* ── CRUD + sub-sections (only when ON and expanded) ── */}
      {isOn && expanded && (
        <div className="border-t border-border/50 px-4 py-3 space-y-4">

          {/* CRUD rows */}
          {CRUD_GROUPS.map(({ type, label: groupLabel, color }) => {
            const nodes = crudNodes.filter((n) => n.crudType === type);
            if (nodes.length === 0) return null;
            return (
              <CrudRow
                key={type}
                groupLabel={groupLabel}
                color={color}
                nodes={nodes}
                granted={granted}
                toggle={toggle}
                disabled={disabled}
                t={t}
              />
            );
          })}

          {/* Sub-sections (form fields, specific action groups) */}
          {subSections.map((sub) => (
            <SubSection
              key={sub.key}
              node={sub}
              granted={granted}
              toggle={toggle}
              disabled={disabled}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── CRUD row ─────────────────────────────────────────────────────────────────

interface CrudRowProps {
  groupLabel: string;
  color: string;
  nodes: PermissionNode[];
  granted: Set<string>;
  toggle: (key: string, on: boolean) => void;
  disabled: boolean;
  t: (key: string) => string;
}

function CrudRow({ groupLabel, color, nodes, granted, toggle, disabled, t }: CrudRowProps) {
  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
      <span className={cn("w-16 shrink-0 text-xs font-semibold pt-0.5", color)}>
        {groupLabel}
      </span>
      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {nodes.map((node) => (
          <CheckItem
            key={node.key}
            node={node}
            granted={granted}
            toggle={toggle}
            disabled={disabled}
            t={t}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Sub-section (form fields / actions) ─────────────────────────────────────

interface SubSectionProps {
  node: PermissionNode;
  granted: Set<string>;
  toggle: (key: string, on: boolean) => void;
  disabled: boolean;
  t: (key: string) => string;
}

function SubSection({ node, granted, toggle, disabled, t }: SubSectionProps) {
  const [open, setOpen] = useState(false);
  const isOn = granted.has(node.key);
  const { on, total } = countGranted(node.key, granted);

  const label = resolveLabel(t, node);
  const children = node.children ?? [];

  // All leaf items under this sub-section (fields, actions, C/R/U/D)
  const allLeaves = collectByType(children, ['field', 'action', 'C', 'R', 'U', 'D', 'export', 'import']);

  return (
    <div className="rounded-md border border-border/40 bg-muted/10">
      {/* sub-section header */}
      <div className="flex items-center gap-2 px-3 py-2">
        <Switch
          checked={isOn}
          disabled={disabled}
          onCheckedChange={(val) => toggle(node.key, val)}
          className="h-4 w-7 shrink-0 [&>span]:h-3 [&>span]:w-3"
        />
        <span
          className={cn(
            "flex-1 text-xs font-medium select-none",
            isOn ? "text-foreground" : "text-muted-foreground",
          )}
        >
          {label}
        </span>
        {isOn && total > 0 && (
          <span className="text-[10px] tabular-nums text-muted-foreground/60">
            {on}/{total}
          </span>
        )}
        {isOn && allLeaves.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="rounded p-0.5 hover:bg-muted"
          >
            {open
              ? <ChevronDown className="h-3 w-3 text-muted-foreground" />
              : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
          </button>
        )}
      </div>

      {/* expanded leaf items */}
      {isOn && open && allLeaves.length > 0 && (
        <div className="border-t border-border/30 px-3 py-2 flex flex-wrap gap-x-5 gap-y-2">
          {allLeaves.map((leaf) => (
            <CheckItem
              key={leaf.key}
              node={leaf}
              granted={granted}
              toggle={toggle}
              disabled={disabled}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Checkbox item ────────────────────────────────────────────────────────────

interface CheckItemProps {
  node: PermissionNode;
  granted: Set<string>;
  toggle: (key: string, on: boolean) => void;
  disabled: boolean;
  t: (key: string) => string;
}

function CheckItem({ node, granted, toggle, disabled, t }: CheckItemProps) {
  const checked = granted.has(node.key);
  const label = resolveLabel(t, node);

  return (
    <label
      className={cn(
        "flex items-center gap-1.5 cursor-pointer select-none",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <Checkbox
        checked={checked}
        disabled={disabled}
        onCheckedChange={(val) => toggle(node.key, !!val)}
        className="h-3.5 w-3.5"
      />
      <span className={cn("text-xs", checked ? "text-foreground" : "text-muted-foreground")}>
        {label}
      </span>
    </label>
  );
}

// ─── Label resolver ───────────────────────────────────────────────────────────

function resolveLabel(t: (key: string) => string, node: PermissionNode): string {
  const translated = t(node.labelKey);
  // If translation returns the key itself, fall back to a humanized version of the last segment
  if (translated === node.labelKey) {
    const segment = node.key.split('.').pop() ?? node.key;
    return segment.replace(/([A-Z])/g, ' $1').replace(/[-_]/g, ' ').trim();
  }
  return translated;
}
