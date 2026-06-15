export interface PermissionGroup {
  id: string;
  label: string;
  description: string;
  permissions: string[];
}

export type PermissionGroupState = "none" | "partial" | "all";

const definitions: PermissionGroup[] = [
  {
    id: "users",
    label: "使用者管理",
    description: "查看與管理員工帳號。",
    permissions: ["users.read", "users.manage"],
  },
  {
    id: "roles",
    label: "角色與權限管理",
    description: "查看、建立及調整角色權限。",
    permissions: ["roles.read", "roles.manage", "permissions.read"],
  },
  {
    id: "access-grants",
    label: "資源授權管理",
    description: "查看與調整客戶、任務的存取範圍。",
    permissions: [
      "access-grants.read",
      "access-grants.manage",
      "authorization.evaluate",
    ],
  },
  {
    id: "departments",
    label: "部門管理",
    description: "查看、建立、編輯及封存部門。",
    permissions: ["departments.read", "departments.manage"],
  },
  {
    id: "customers",
    label: "客戶管理",
    description: "查看、新增、編輯及封存客戶。",
    permissions: [
      "customers.read",
      "customers.create",
      "customers.update",
      "customers.delete",
    ],
  },
  {
    id: "tasks",
    label: "任務管理",
    description: "查看、新增、編輯及封存 SEO 任務。",
    permissions: [
      "tasks.read",
      "tasks.create",
      "tasks.update",
      "tasks.delete",
    ],
  },
  {
    id: "audit-events",
    label: "稽核紀錄",
    description: "查看帳號、角色與權限異動紀錄。",
    permissions: ["audit-events.read"],
  },
];

export function buildPermissionGroups(
  availablePermissions: readonly string[],
): PermissionGroup[] {
  const available = new Set(availablePermissions);
  const known = new Set(definitions.flatMap((group) => group.permissions));
  const groups = definitions
    .map((group) => ({
      ...group,
      permissions: group.permissions.filter((permission) =>
        available.has(permission),
      ),
    }))
    .filter((group) => group.permissions.length);
  const unknown = availablePermissions.filter(
    (permission) => !known.has(permission),
  );

  if (unknown.length) {
    groups.push({
      id: "other",
      label: "其他權限",
      description: "尚未分類的新功能權限。",
      permissions: [...unknown],
    });
  }

  return groups;
}

export function permissionGroupState(
  selectedPermissions: readonly string[],
  groupPermissions: readonly string[],
): PermissionGroupState {
  const selected = new Set(selectedPermissions);
  const selectedCount = groupPermissions.filter((permission) =>
    selected.has(permission),
  ).length;

  if (selectedCount === 0) return "none";
  if (selectedCount === groupPermissions.length) return "all";
  return "partial";
}

export function togglePermissionGroup(
  selectedPermissions: readonly string[],
  groupPermissions: readonly string[],
): string[] {
  const selected = new Set(selectedPermissions);
  const removeGroup =
    permissionGroupState(selectedPermissions, groupPermissions) === "all";

  for (const permission of groupPermissions) {
    if (removeGroup) selected.delete(permission);
    else selected.add(permission);
  }

  return [...selected];
}
