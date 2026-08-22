"use client";

import { useState, useCallback } from "react";
import { ChevronRight } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import type { PermissionNode } from "@/lib/permission-registry";
import { getDescendantKeys, getAncestorKeys } from "@/lib/permission-registry";

interface PermissionTreeProps {
  registry: PermissionNode[];
  granted: Set<string>;
  onToggle: (key: string, on: boolean) => void;
  disabled?: boolean;
}

export function PermissionTree({
  registry,
  granted,
  onToggle,
  disabled = false,
}: PermissionTreeProps) {
  return (
    <div className="space-y-0.5">
      {registry.map((node) => (
        <TreeNode
          key={node.key}
          node={node}
          granted={granted}
          onToggle={onToggle}
          disabled={disabled}
          depth={0}
        />
      ))}
    </div>
  );
}

interface TreeNodeProps {
  node: PermissionNode;
  granted: Set<string>;
  onToggle: (key: string, on: boolean) => void;
  disabled: boolean;
  depth: number;
}

function TreeNode({
  node,
  granted,
  onToggle,
  disabled,
  depth,
}: TreeNodeProps) {
  const t = useT();
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = !!node.children?.length;
  const isOn = granted.has(node.key);

  const handleToggle = useCallback(
    (on: boolean) => {
      if (disabled) return;
      onToggle(node.key, on);

      if (on) {
        // Turn on all ancestors
        for (const ancestor of getAncestorKeys(node.key)) {
          if (!granted.has(ancestor)) {
            onToggle(ancestor, true);
          }
        }
        // Turn on all descendants
        if (hasChildren) {
          for (const desc of getDescendantKeys(node.key)) {
            if (!granted.has(desc)) {
              onToggle(desc, true);
            }
          }
        }
      } else {
        // Turn off all descendants
        if (hasChildren) {
          for (const desc of getDescendantKeys(node.key)) {
            if (granted.has(desc)) {
              onToggle(desc, false);
            }
          }
        }
      }
    },
    [node.key, granted, onToggle, disabled, hasChildren],
  );

  // Calculate how many descendants are on vs total
  let countOn = 0;
  let countTotal = 0;
  if (hasChildren) {
    const descendants = getDescendantKeys(node.key);
    countTotal = descendants.length;
    countOn = descendants.filter((k) => granted.has(k)).length;
  }

  // Resolve label: try t() with labelKey, fall back to key
  let label: string;
  const translated = t(node.labelKey);
  label = translated !== node.labelKey ? translated : node.key;

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50 transition-colors",
          depth === 0 && "bg-muted/30",
        )}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {/* Expand/collapse toggle */}
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-muted"
          >
            <ChevronRight
              className={cn(
                "h-3.5 w-3.5 text-muted-foreground transition-transform",
                expanded && "rotate-90",
              )}
            />
          </button>
        ) : (
          <span className="w-5 shrink-0" />
        )}

        {/* Switch */}
        <Switch
          checked={isOn}
          disabled={disabled}
          onCheckedChange={handleToggle}
          className="shrink-0"
        />

        {/* Label */}
        <span
          className={cn(
            "text-sm select-none",
            isOn ? "text-foreground" : "text-muted-foreground",
            depth === 0 && "font-medium",
          )}
        >
          {label}
        </span>

        {/* Count badge for parent nodes */}
        {hasChildren && (
          <span className="ml-auto text-[10px] text-muted-foreground/60 tabular-nums">
            {countOn}/{countTotal}
          </span>
        )}
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNode
              key={child.key}
              node={child}
              granted={granted}
              onToggle={onToggle}
              disabled={disabled}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
