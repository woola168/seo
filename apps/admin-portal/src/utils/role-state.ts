import type { Role } from "../types";

export function removeRoleById(roles: Role[], roleId: string): Role[] {
  return roles.filter((role) => role.id !== roleId);
}
