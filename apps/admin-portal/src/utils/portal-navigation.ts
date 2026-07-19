import type { NavigationItem } from "../types";
import { buildGeoNavigation } from "./geo-navigation";
import { hasPermission } from "./permissions";

const permissionChildren: Array<{
  item: NavigationItem;
  requiredPermission: string;
}> = [
  {
    item: {
      id: "permissions-members",
      label: "成員管理",
      icon: "users",
      page: "permissions-members",
    },
    requiredPermission: "users.read",
  },
  {
    item: {
      id: "permissions-roles",
      label: "角色管理",
      icon: "shield",
      page: "permissions-roles",
    },
    requiredPermission: "roles.read",
  },
  {
    item: {
      id: "permissions-departments",
      label: "部門管理",
      icon: "briefcase",
      page: "permissions-departments",
    },
    requiredPermission: "departments.read",
  },
  {
    item: {
      id: "permissions-authorization",
      label: "授權判斷",
      icon: "check-circle",
      page: "permissions-authorization",
    },
    requiredPermission: "authorization.evaluate",
  },
];

export function buildPortalNavigation(
  permissions: readonly string[],
): NavigationItem[] {
  const visiblePermissionChildren = permissionChildren
    .filter(({ requiredPermission }) => hasPermission(permissions, requiredPermission))
    .map(({ item }) => item);

  return [
    {
      id: "dashboard",
      label: "總覽",
      icon: "grid",
      page: "dashboard",
      disabled: true,
    },
    ...(hasPermissionPrefix(permissions, "customers.")
      ? [{
          id: "clients",
          label: "客戶",
          icon: "users",
          group: "專案管理",
          disabled: true,
        } satisfies NavigationItem]
      : []),
    ...(hasPermissionPrefix(permissions, "tasks.")
      ? [{
          id: "tasks",
          label: "任務",
          icon: "briefcase",
          group: "專案管理",
          badge: "9",
          disabled: true,
        } satisfies NavigationItem]
      : []),
    ...buildGeoNavigation(permissions),
    ...(visiblePermissionChildren.length
      ? [{
          id: "permissions",
          label: "權限管理",
          icon: "shield",
          group: "系統",
          children: visiblePermissionChildren,
        } satisfies NavigationItem]
      : []),
    {
      id: "settings",
      label: "系統設定",
      icon: "settings",
      group: "系統",
      disabled: true,
    },
  ];
}

function hasPermissionPrefix(
  permissions: readonly string[],
  prefix: string,
): boolean {
  return permissions.some((permission) => permission.startsWith(prefix));
}
