import type {
  MemberQuery,
  MemberSortField,
  MemberView,
  PaginatedMembers,
} from "../types";

export function queryMembers(
  members: MemberView[],
  query: MemberQuery,
): PaginatedMembers {
  const search = query.search.trim().toLocaleLowerCase("zh-TW");
  const filtered = members.filter((member) => {
    const matchesSearch =
      !search ||
      member.displayName.toLocaleLowerCase("zh-TW").includes(search) ||
      member.email.toLocaleLowerCase("zh-TW").includes(search);
    return (
      matchesSearch &&
      (!query.role || member.roleNames.includes(query.role)) &&
      (!query.department || member.department === query.department) &&
      (!query.status || member.status === query.status)
    );
  });

  const direction = query.sortDirection === "asc" ? 1 : -1;
  filtered.sort(
    (left, right) =>
      memberSortValue(left, query.sortField).localeCompare(
        memberSortValue(right, query.sortField),
        "zh-TW",
        { numeric: true },
      ) * direction,
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / query.pageSize));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * query.pageSize;
  return {
    items: filtered.slice(start, start + query.pageSize),
    total: filtered.length,
    totalPages,
    page,
  };
}

function memberSortValue(
  member: MemberView,
  field: MemberSortField,
): string {
  switch (field) {
    case "role":
      return member.roleNames.join(",");
    case "department":
      return member.department ?? "";
    case "lastLogin":
      return member.lastLogin ?? "";
    default:
      return member[field];
  }
}
