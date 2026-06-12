import { describe, expect, it } from "vitest";

import { queryMembers } from "./member-query";
import type { MemberQuery, MemberView } from "../types";

const members: MemberView[] = [
  {
    id: "1",
    email: "amy@example.com",
    displayName: "Amy",
    status: "active",
    roleIds: ["editor"],
    roleNames: ["editor"],
    customerIds: [],
    taskIds: [],
    department: "行銷部",
    lastLogin: "2026/06/10 上午10:00",
    source: "workspace",
    color: "#0a2b41",
  },
  {
    id: "2",
    email: "ben@example.com",
    displayName: "Ben",
    status: "invited",
    roleIds: ["viewer"],
    roleNames: ["viewer"],
    customerIds: [],
    taskIds: [],
    department: "工程部",
    lastLogin: null,
    source: "external",
    color: "#1677ff",
  },
  {
    id: "3",
    email: "chris@example.com",
    displayName: "Chris",
    status: "active",
    roleIds: ["viewer"],
    roleNames: ["viewer"],
    customerIds: [],
    taskIds: [],
    department: "工程部",
    lastLogin: "2026/06/08 上午10:00",
    source: "external",
    color: "#52c41a",
  },
];

const baseQuery: MemberQuery = {
  search: "",
  role: "",
  department: "",
  status: "",
  sortField: "displayName",
  sortDirection: "asc",
  page: 1,
  pageSize: 2,
};

describe("queryMembers", () => {
  it("filters members by search, role, department and status", () => {
    const result = queryMembers(members, {
      ...baseQuery,
      search: "chris",
      role: "viewer",
      department: "工程部",
      status: "active",
    });

    expect(result.items.map((member) => member.displayName)).toEqual(["Chris"]);
  });

  it("sorts and paginates the filtered result", () => {
    const result = queryMembers(members, {
      ...baseQuery,
      sortDirection: "desc",
      page: 2,
    });

    expect(result.total).toBe(3);
    expect(result.totalPages).toBe(2);
    expect(result.items.map((member) => member.displayName)).toEqual(["Amy"]);
  });

  it("clamps a page outside the available range", () => {
    const result = queryMembers(members, { ...baseQuery, page: 99 });

    expect(result.page).toBe(2);
  });
});
