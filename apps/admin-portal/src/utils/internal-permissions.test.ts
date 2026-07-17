import { describe, expect, it } from "vitest";

import { filterAssignablePermissions } from "./internal-permissions";

describe("internal permissions", () => {
  it("removes internal permissions without dropping other hidden permissions", () => {
    expect(
      filterAssignablePermissions([
        "geo.admin.access",
        "geo.projects.read",
        "customers.read",
      ]),
    ).toEqual(["geo.projects.read", "customers.read"]);
  });
});
