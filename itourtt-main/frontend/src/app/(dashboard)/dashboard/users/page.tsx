"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Shield,
  Plus,
  Loader2,
  UserPlus,
  Users,
  Trash2,
  Pencil,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSortable } from "@/hooks/use-sortable";
import { SortableHeader } from "@/components/sortable-header";
import { TableFilterBar } from "@/components/table-filter-bar";
import { PermissionMatrix } from "@/components/permission-matrix";
import { UserSessionsDialog } from "@/components/user-sessions-dialog";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { formatDate } from "@/lib/utils";
import { usePermission } from "@/hooks/use-permission";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";

const USERS_COL_DEFS: ColumnDef[] = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email" },
  { key: "role", label: "Role" },
  { key: "status", label: "Status" },
  { key: "created", label: "Created" },
  { key: "actions", label: "Actions" },
];

// ─── Types ──────────────────────────────────────────────────────────────────
interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  roleId?: string;
  roleRef?: { name: string; slug: string };
  isActive: boolean;
  createdAt: string;
}

interface Role {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  isSystem: boolean;
  isActive: boolean;
  userCount: number;
  permissionCount: number;
  createdAt: string;
  updatedAt: string;
}

interface RoleDetail extends Role {
  permissionKeys: string[];
}

// ─── Main Page ──────────────────────────────────────────────────────────────
export default function UsersPage() {
  const t = useT();

  // Permission checks
  const canAddUser         = usePermission("users.addButton");
  const canEditUser        = usePermission("users.table.editButton");
  const canChangeRole      = usePermission("users.table.changeRole");
  const canDeactivateUser  = usePermission("users.table.deactivate");
  const canAddRole         = usePermission("users.roles.addButton");
  const canEditRole        = usePermission("users.roles.editButton");
  const canDeleteRole      = usePermission("users.roles.deleteButton");
  const canEditPermissions = usePermission("users.roles.editPermissions");

  const [activeTab, setActiveTab] = useState("users");

  // ─── Users tab state ────────────────────────────────────────────────────
  const [users, setUsers]           = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [search, setSearch]         = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [statusTab, setStatusTab]   = useState<"active" | "inactive">("active");

  const activeCount = useMemo(() => users.filter((u) => u.isActive).length, [users]);
  const inactiveCount = users.length - activeCount;

  const filtered = useMemo(() => {
    let result = users.filter((u) => u.isActive === (statusTab === "active"));
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
      );
    }
    if (roleFilter !== "ALL") {
      result = result.filter((u) => u.role === roleFilter);
    }
    return result;
  }, [users, search, roleFilter, statusTab]);

  const { sortedData, sortKey, sortDir, onSort } = useSortable(filtered);
  const { visibility: userColVis, saveVisibility: saveUserColVis } = useColumnPreferences("users_list", USERS_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => userColVis[key] !== false;

  const [addDialogOpen, setAddDialogOpen]   = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [sessionsUser, setSessionsUser] = useState<User | null>(null);
  const [editingUser, setEditingUser]       = useState<User | null>(null);
  const [formName, setFormName]             = useState("");
  const [formEmail, setFormEmail]           = useState("");
  const [formPassword, setFormPassword]     = useState("");
  const [formRoleId, setFormRoleId]         = useState("");
  const [submitting, setSubmitting]         = useState(false);

  // ─── Roles & Permissions tab state ──────────────────────────────────────
  const [roles, setRoles]                   = useState<Role[]>([]);
  const [rolesLoading, setRolesLoading]     = useState(false);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [roleDetail, setRoleDetail]         = useState<RoleDetail | null>(null);
  const [roleDetailLoading, setRoleDetailLoading] = useState(false);
  const [grantedKeys, setGrantedKeys]       = useState<Set<string>>(new Set());
  const [permsDirty, setPermsDirty]         = useState(false);
  const [permsSaving, setPermsSaving]       = useState(false);

  // Role create/edit dialog
  const [roleDialogOpen, setRoleDialogOpen]   = useState(false);
  const [roleDialogMode, setRoleDialogMode]   = useState<"create" | "edit">("create");
  const [roleFormName, setRoleFormName]       = useState("");
  const [roleFormDescription, setRoleFormDescription] = useState("");
  const [roleSubmitting, setRoleSubmitting]   = useState(false);

  // ─── Fetch users ─────────────────────────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const { data } = await api.get("/users?limit=1000");
      setUsers(Array.isArray(data.data) ? data.data : []);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        t("users.failedLoadUsers");
      toast.error(message);
    } finally {
      setUsersLoading(false);
    }
  }, [t]);

  // ─── Fetch roles ──────────────────────────────────────────────────────────
  const fetchRoles = useCallback(async () => {
    setRolesLoading(true);
    try {
      const { data } = await api.get("/permissions/roles");
      setRoles(Array.isArray(data) ? data : []);
    } catch {
      setRoles([]);
    } finally {
      setRolesLoading(false);
    }
  }, []);

  // ─── Fetch role detail ────────────────────────────────────────────────────
  const fetchRoleDetail = useCallback(async (roleId: string) => {
    setRoleDetailLoading(true);
    try {
      const { data } = await api.get(`/permissions/roles/${roleId}`);
      setRoleDetail(data);
      setGrantedKeys(new Set(data.permissionKeys || []));
      setPermsDirty(false);
    } catch {
      toast.error("Failed to load role details");
    } finally {
      setRoleDetailLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);
  useEffect(() => { fetchRoles(); }, [fetchRoles]);

  useEffect(() => {
    if (selectedRoleId) fetchRoleDetail(selectedRoleId);
  }, [selectedRoleId, fetchRoleDetail]);

  // Auto-select first role
  useEffect(() => {
    if (roles.length > 0 && !selectedRoleId) setSelectedRoleId(roles[0].id);
  }, [roles, selectedRoleId]);

  // ─── Create user ──────────────────────────────────────────────────────────
  async function handleCreate() {
    if (!formName.trim() || !formEmail.trim() || !formPassword.trim()) {
      toast.error(t("users.allFieldsRequired"));
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/users", {
        name: formName.trim(),
        email: formEmail.trim(),
        password: formPassword.trim(),
        role: "VIEWER",
        ...(formRoleId && { roleId: formRoleId }),
      });
      toast.success(t("users.userCreated"));
      setAddDialogOpen(false);
      resetForm();
      fetchUsers();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        t("users.failedCreateUser");
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  // ─── Edit user ────────────────────────────────────────────────────────────
  function openEdit(user: User) {
    setEditingUser(user);
    setFormName(user.name);
    setFormEmail(user.email);
    setFormRoleId(user.roleId || "");
    setEditDialogOpen(true);
  }

  async function handleEdit() {
    if (!editingUser) return;
    setSubmitting(true);
    try {
      await api.patch(`/users/${editingUser.id}`, {
        name: formName.trim(),
        email: formEmail.trim(),
      });
      if (formRoleId && formRoleId !== editingUser.roleId) {
        await api.patch(`/users/${editingUser.id}/role`, {
          role: roles.find((r) => r.id === formRoleId)?.slug?.toUpperCase() || editingUser.role,
          roleId: formRoleId,
        });
      }
      if (formPassword.trim()) {
        await api.patch(`/users/${editingUser.id}/password`, { newPassword: formPassword.trim() });
      }
      toast.success(t("users.userUpdated"));
      setEditDialogOpen(false);
      resetForm();
      fetchUsers();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        t("users.failedUpdateUser");
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  // ─── Deactivate user ──────────────────────────────────────────────────────
  async function handleDeactivate(id: string) {
    try {
      await api.delete(`/users/${id}`);
      toast.success(t("users.userDeactivated"));
      fetchUsers();
    } catch {
      toast.error(t("users.failedDeactivateUser"));
    }
  }

  // ─── Reactivate user ──────────────────────────────────────────────────────
  async function handleReactivate(id: string) {
    try {
      await api.patch(`/users/${id}/reactivate`);
      toast.success(t("users.userReactivated"));
      fetchUsers();
    } catch {
      toast.error(t("users.failedReactivateUser"));
    }
  }

  // ─── Permission matrix change ─────────────────────────────────────────────
  function handlePermissionsChange(next: Set<string>) {
    setGrantedKeys(next);
    setPermsDirty(true);
  }

  // ─── Save permissions ─────────────────────────────────────────────────────
  async function handleSavePermissions() {
    if (!selectedRoleId) return;
    setPermsSaving(true);
    try {
      await api.put(`/permissions/roles/${selectedRoleId}/permissions`, {
        permissionKeys: Array.from(grantedKeys),
      });
      toast.success("Permissions saved successfully");
      setPermsDirty(false);
      fetchRoles();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        "Failed to save permissions";
      toast.error(message);
    } finally {
      setPermsSaving(false);
    }
  }

  // ─── Seed defaults ────────────────────────────────────────────────────────
  async function handleSeedDefaults() {
    try {
      await api.post("/permissions/seed");
      toast.success("System roles seeded successfully");
      fetchRoles();
      if (selectedRoleId) fetchRoleDetail(selectedRoleId);
    } catch {
      toast.error("Failed to seed defaults");
    }
  }

  // ─── Role CRUD ────────────────────────────────────────────────────────────
  function openCreateRole() {
    setRoleDialogMode("create");
    setRoleFormName("");
    setRoleFormDescription("");
    setRoleDialogOpen(true);
  }

  function openEditRole(role: Role) {
    setRoleDialogMode("edit");
    setRoleFormName(role.name);
    setRoleFormDescription(role.description || "");
    setRoleDialogOpen(true);
  }

  async function handleRoleSubmit() {
    if (!roleFormName.trim()) { toast.error("Role name is required"); return; }
    setRoleSubmitting(true);
    try {
      if (roleDialogMode === "create") {
        const { data } = await api.post("/permissions/roles", {
          name: roleFormName.trim(),
          description: roleFormDescription.trim() || undefined,
        });
        toast.success("Role created");
        setSelectedRoleId(data.id);
      } else if (selectedRoleId) {
        await api.patch(`/permissions/roles/${selectedRoleId}`, {
          name: roleFormName.trim(),
          description: roleFormDescription.trim() || undefined,
        });
        toast.success("Role updated");
      }
      setRoleDialogOpen(false);
      fetchRoles();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        "Failed to save role";
      toast.error(message);
    } finally {
      setRoleSubmitting(false);
    }
  }

  async function handleDeleteRole(id: string) {
    try {
      await api.delete(`/permissions/roles/${id}`);
      toast.success("Role deleted");
      if (selectedRoleId === id) setSelectedRoleId(null);
      fetchRoles();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        "Failed to delete role";
      toast.error(message);
    }
  }

  function resetForm() {
    setFormName(""); setFormEmail(""); setFormPassword(""); setFormRoleId(""); setEditingUser(null);
  }

  const roleOptions = useMemo(() => roles.filter((r) => r.isActive), [roles]);

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <PageHeader title={t("users.title")} description={t("users.description")} />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="border-border bg-muted">
          <TabsTrigger value="users">{t("users.usersTab")}</TabsTrigger>
          <TabsTrigger value="permissions">
            <Shield className="mr-1.5 h-3.5 w-3.5" />
            Roles & Permissions
          </TabsTrigger>
        </TabsList>

        {/* ─── Tab 1: Users ─────────────────────────────────── */}
        <TabsContent value="users" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{t("users.usersDescription")}</p>
            {canAddUser && (
              <Button size="sm" className="gap-1.5" onClick={() => { resetForm(); setAddDialogOpen(true); }}>
                <UserPlus className="h-4 w-4" />
                {t("users.addUser")}
              </Button>
            )}
          </div>

          {usersLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : users.length === 0 ? (
            <div className="py-16">
              <EmptyState
                icon={Users}
                heading="No users yet"
                description="Add users to grant access to the system."
              />
            </div>
          ) : (
            <>
              <Tabs value={statusTab} onValueChange={(v) => setStatusTab(v as "active" | "inactive")}>
                <TabsList className="border-border bg-muted">
                  <TabsTrigger value="active">
                    {t("users.activeTab")}
                    <Badge variant="secondary" className="ml-1.5">{activeCount}</Badge>
                  </TabsTrigger>
                  <TabsTrigger value="inactive">
                    {t("users.inactiveTab")}
                    <Badge variant="secondary" className="ml-1.5">{inactiveCount}</Badge>
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              <TableFilterBar
                search={search}
                onSearchChange={setSearch}
                placeholder={t("common.search") + "..."}
                statusOptions={[
                  { value: "ALL",           label: t("common.all") },
                  { value: "ADMIN",         label: "Admin" },
                  { value: "DISPATCHER",    label: "Dispatcher" },
                  { value: "ACCOUNTANT",    label: "Accountant" },
                  { value: "AGENT_MANAGER", label: "Agent Manager" },
                  { value: "VIEWER",        label: "Viewer" },
                ]}
                statusValue={roleFilter}
                onStatusChange={setRoleFilter}
                statusPlaceholder={t("common.all")}
              />
              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={USERS_COL_DEFS} visibility={userColVis} onSave={saveUserColVis} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted">
                      {isVis("name") && <SortableHeader label={t("common.name")} sortKey="name" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                      {isVis("email") && <SortableHeader label={t("common.email")} sortKey="email" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                      {isVis("role") && <SortableHeader label={t("common.role")} sortKey="role" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                      {isVis("status") && <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>}
                      {isVis("created") && <TableHead className="text-muted-foreground text-xs">{t("users.created")}</TableHead>}
                      {isVis("actions") && <TableHead className="text-right text-muted-foreground text-xs">{t("common.actions")}</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedData.map((user, idx) => (
                      <TableRow
                        key={user.id}
                        className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                      >
                        {isVis("name") && <TableCell className="font-medium text-foreground">{user.name}</TableCell>}
                        {isVis("email") && <TableCell className="text-muted-foreground">{user.email}</TableCell>}
                        {isVis("role") && <TableCell><Badge variant="secondary">{user.roleRef?.name || t(`role.${user.role}`)}</Badge></TableCell>}
                        {isVis("status") && <TableCell>{user.isActive ? <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">{t("common.active")}</Badge> : <Badge className="bg-red-500/20 text-red-600 dark:text-red-400">{t("common.inactive")}</Badge>}</TableCell>}
                        {isVis("created") && <TableCell className="text-muted-foreground">{formatDate(user.createdAt)}</TableCell>}
                        {isVis("actions") && (
                          <TableCell className="text-right">
                            {canEditUser && <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => openEdit(user)}>{t("common.edit")}</Button>}
                            {canEditUser && <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => setSessionsUser(user)}>Sessions</Button>}
                            {canDeactivateUser && user.isActive && <Button variant="ghost" size="sm" className="text-red-500/70 hover:text-red-500" onClick={() => handleDeactivate(user.id)}>{t("users.deactivate")}</Button>}
                            {canDeactivateUser && !user.isActive && <Button variant="ghost" size="sm" className="text-emerald-600/70 hover:text-emerald-600" onClick={() => handleReactivate(user.id)}>{t("users.reactivate")}</Button>}
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                    {sortedData.length === 0 && (
                      <TableRow className="border-border">
                        <TableCell colSpan={USERS_COL_DEFS.length} className="py-10 text-center text-muted-foreground">
                          {t("common.noData")}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>

        {/* ─── Tab 2: Roles & Permissions (Matrix) ──────────── */}
        <TabsContent value="permissions" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Toggle sections ON/OFF to control visibility. When ON, use the CRUD checkboxes to fine-tune access.
            </p>
            <Button variant="outline" size="sm" onClick={handleSeedDefaults}>
              Seed Defaults
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Left: Role list */}
            <div className="lg:col-span-3">
              <Card className="border-border bg-card p-3 space-y-2">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-foreground">Roles</h3>
                  {canAddRole && (
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={openCreateRole}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                {rolesLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : roles.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">
                    No roles found. Click &quot;Seed Defaults&quot; to create system roles.
                  </p>
                ) : (
                  <div className="space-y-1">
                    {roles.map((role) => (
                      <div
                        key={role.id}
                        className={`flex items-center justify-between rounded-md px-2.5 py-2 cursor-pointer transition-colors ${
                          selectedRoleId === role.id
                            ? "bg-accent text-accent-foreground"
                            : "hover:bg-muted/50 text-foreground"
                        }`}
                        onClick={() => setSelectedRoleId(role.id)}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm font-medium truncate">{role.name}</span>
                            {role.isSystem && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 shrink-0">
                                System
                              </Badge>
                            )}
                          </div>
                          <span className="text-[10px] text-muted-foreground">
                            {role.userCount} user{role.userCount !== 1 ? "s" : ""} · {role.permissionCount} perms
                          </span>
                        </div>
                        {!role.isSystem && selectedRoleId === role.id && (
                          <div className="flex shrink-0 gap-0.5">
                            {canEditRole && (
                              <button
                                className="p-1 rounded hover:bg-background"
                                onClick={(e) => { e.stopPropagation(); openEditRole(role); }}
                              >
                                <Pencil className="h-3 w-3 text-muted-foreground" />
                              </button>
                            )}
                            {canDeleteRole && (
                              <button
                                className="p-1 rounded hover:bg-background"
                                onClick={(e) => { e.stopPropagation(); handleDeleteRole(role.id); }}
                              >
                                <Trash2 className="h-3 w-3 text-red-500/70" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>

            {/* Right: Permission Matrix */}
            <div className="lg:col-span-9">
              <Card className="border-border bg-card p-4">
                {!selectedRoleId ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Shield className="mb-2 h-8 w-8" />
                    <p className="text-sm">Select a role to view and edit permissions</p>
                  </div>
                ) : roleDetailLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : roleDetail ? (
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-base font-medium text-foreground">{roleDetail.name}</h3>
                        {roleDetail.description && (
                          <p className="text-xs text-muted-foreground mt-0.5">{roleDetail.description}</p>
                        )}
                      </div>
                      <div className="flex gap-2">
                        {permsDirty && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => { if (selectedRoleId) fetchRoleDetail(selectedRoleId); }}
                          >
                            Discard
                          </Button>
                        )}
                        {canEditPermissions && (
                          <Button
                            size="sm"
                            disabled={!permsDirty || permsSaving || roleDetail.slug === "admin"}
                            onClick={handleSavePermissions}
                            className="gap-1.5"
                          >
                            {permsSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                            Save Permissions
                          </Button>
                        )}
                      </div>
                    </div>

                    {roleDetail.slug === "admin" && (
                      <div className="rounded-md bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
                        Admin role has full access to all permissions and cannot be modified.
                      </div>
                    )}

                    {/* Legend */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 rounded-md bg-muted/30 px-3 py-2 text-[10px]">
                      <span className="text-emerald-500 font-medium">Create</span>
                      <span className="text-blue-400 font-medium">Read</span>
                      <span className="text-amber-400 font-medium">Update</span>
                      <span className="text-red-400 font-medium">Delete</span>
                      <span className="text-purple-400 font-medium">Export</span>
                      <span className="text-cyan-400 font-medium">Import</span>
                      <span className="text-orange-400 font-medium">Actions</span>
                      <span className="ml-auto text-muted-foreground italic">Toggle section ON to expand controls</span>
                    </div>

                    {/* Matrix */}
                    <div className="max-h-[calc(100vh-340px)] overflow-y-auto pr-1 space-y-1">
                      <PermissionMatrix
                        granted={grantedKeys}
                        onChange={handlePermissionsChange}
                        disabled={roleDetail.slug === "admin"}
                      />
                    </div>
                  </div>
                ) : null}
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* ─── Add User Dialog ──────────────────────────────────── */}
      <Dialog open={addDialogOpen} onOpenChange={(open) => { setAddDialogOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader><DialogTitle>{t("users.addUser")}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.name")}</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Full name" className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.email")}</Label>
              <Input type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} placeholder="user@example.com" className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.password")}</Label>
              <Input type="password" value={formPassword} onChange={(e) => setFormPassword(e.target.value)} placeholder="Min 6 characters" className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.role")}</Label>
              <Select value={formRoleId} onValueChange={setFormRoleId}>
                <SelectTrigger className="border-border bg-muted/50 text-foreground">
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-popover-foreground">
                  {roleOptions.map((r) => (
                    <SelectItem key={r.id} value={r.id} className="focus:bg-accent focus:text-accent-foreground">{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAddDialogOpen(false)}>{t("common.cancel")}</Button>
            <Button onClick={handleCreate} disabled={submitting} className="gap-1.5">
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Edit User Dialog ─────────────────────────────────── */}
      <Dialog open={editDialogOpen} onOpenChange={(open) => { setEditDialogOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader><DialogTitle>{t("users.editUser")}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.name")}</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.email")}</Label>
              <Input type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
            {canChangeRole && (
              <div className="space-y-2">
                <Label className="text-foreground/70">{t("common.role")}</Label>
                <Select value={formRoleId} onValueChange={setFormRoleId}>
                  <SelectTrigger className="border-border bg-muted/50 text-foreground">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent className="border-border bg-popover text-popover-foreground">
                    {roleOptions.map((r) => (
                      <SelectItem key={r.id} value={r.id} className="focus:bg-accent focus:text-accent-foreground">{r.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label className="text-foreground/70">{t("common.password")}</Label>
              <Input type="password" value={formPassword} onChange={(e) => setFormPassword(e.target.value)} placeholder="Leave blank to keep current" className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditDialogOpen(false)}>{t("common.cancel")}</Button>
            <Button onClick={handleEdit} disabled={submitting} className="gap-1.5">
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Role Create/Edit Dialog ──────────────────────────── */}
      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{roleDialogMode === "create" ? "Create Role" : "Edit Role"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-foreground/70">Role Name</Label>
              <Input value={roleFormName} onChange={(e) => setRoleFormName(e.target.value)} placeholder="e.g. Senior Accountant" className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">Description</Label>
              <Input value={roleFormDescription} onChange={(e) => setRoleFormDescription(e.target.value)} placeholder="Optional description" className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRoleDialogOpen(false)}>{t("common.cancel")}</Button>
            <Button onClick={handleRoleSubmit} disabled={roleSubmitting} className="gap-1.5">
              {roleSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {roleDialogMode === "create" ? t("common.create") : t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <UserSessionsDialog
        userId={sessionsUser?.id ?? null}
        userName={sessionsUser?.name}
        open={!!sessionsUser}
        onOpenChange={(v) => { if (!v) setSessionsUser(null); }}
      />
    </div>
  );
}
