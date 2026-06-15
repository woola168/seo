import type {
  MemberMetadata,
  MemberView,
  Role,
  UserAccess,
} from "../types";

const colors = ["#0a2b41", "#1677ff", "#52c41a", "#8b5cf6", "#d68c24"];

export function mergeMemberMetadata(
  users: UserAccess[],
  roles: Role[],
  departmentNames: Map<string, string>,
): MemberView[] {
  const roleNames = new Map(roles.map((role) => [role.id, role.name]));

  return users.map((user, index) => {
    const metadata: MemberMetadata = {
      department: user.departmentId
        ? departmentNames.get(user.departmentId) ?? null
        : null,
      lastLogin: user.lastLoginAt
        ? new Intl.DateTimeFormat("zh-TW", {
            dateStyle: "short",
            timeStyle: "short",
          }).format(new Date(user.lastLoginAt))
        : null,
      source: user.authProvider === "password" ? "workspace" : "external",
      color: colors[index % colors.length] ?? "#0a2b41",
    };
    return {
      ...user,
      ...metadata,
      roleNames: user.roleIds
        .map((roleId) => roleNames.get(roleId))
        .filter((name): name is string => Boolean(name)),
    };
  });
}
