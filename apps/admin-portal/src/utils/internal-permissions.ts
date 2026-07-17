export const GEO_ADMIN_ACCESS = "geo.admin.access";

const internalPermissions = new Set([GEO_ADMIN_ACCESS]);

export function filterAssignablePermissions(
  permissions: readonly string[],
): string[] {
  return permissions.filter((permission) => !internalPermissions.has(permission));
}
