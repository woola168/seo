import type {
  Department,
  MemberMetadata,
  MemberView,
  Role,
  UserAccess,
} from "../types";

const colors = ["#0a2b41", "#1677ff", "#52c41a", "#8b5cf6", "#d68c24"];
const departments = ["決策層", "工程部", "SEO 策略部", "行銷部"];

// TODO(API): Replace department, lastLogin and source after user management APIs expose them.
export function mergeMemberMetadata(
  users: UserAccess[],
  roles: Role[],
): MemberView[] {
  const roleNames = new Map(roles.map((role) => [role.id, role.name]));

  return users.map((user, index) => {
    const metadata: MemberMetadata = {
      department: departments[index % departments.length] ?? null,
      lastLogin:
        user.status === "invited"
          ? null
          : `2026/06/${String(Math.max(1, 12 - index)).padStart(2, "0")} 上午10:${String(index * 7).padStart(2, "0")}`,
      source: index % 3 === 0 ? "workspace" : "external",
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

// TODO(API): Replace this list when department management endpoints exist.
export const mockDepartments: Department[] = [
  {
    id: "leadership",
    name: "決策層",
    description: "產品方向、營運與最終核准。",
    memberCount: 2,
  },
  {
    id: "engineering",
    name: "工程部",
    description: "平台、資料與整合服務開發。",
    memberCount: 4,
  },
  {
    id: "seo-strategy",
    name: "SEO 策略部",
    description: "內容策略、關鍵字與成效分析。",
    memberCount: 5,
  },
  {
    id: "marketing",
    name: "行銷部",
    description: "品牌溝通、活動與客戶協作。",
    memberCount: 3,
  },
];
