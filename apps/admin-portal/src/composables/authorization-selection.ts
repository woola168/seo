export function selectAvailableUserId(
  selectedUserId: string,
  currentUserId: string,
  userIds: readonly string[],
  canEvaluateOthers: boolean,
): string {
  if (selectedUserId === currentUserId) return currentUserId;
  if (canEvaluateOthers && userIds.includes(selectedUserId)) {
    return selectedUserId;
  }
  return currentUserId;
}

export function selectAvailablePermission(
  selectedPermission: string,
  permissions: readonly string[],
): string {
  if (permissions.includes(selectedPermission)) return selectedPermission;
  return permissions[0] ?? "";
}
