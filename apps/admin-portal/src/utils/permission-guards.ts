import { hasPermission } from "./permissions";

export function canManageUserRoles(permissions: readonly string[]): boolean {
  return (
    hasPermission(permissions, "users.manage") &&
    hasPermission(permissions, "roles.read")
  );
}
