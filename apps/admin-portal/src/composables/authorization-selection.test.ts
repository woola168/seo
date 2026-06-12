import { describe, expect, it } from "vitest";

import {
  selectAvailablePermission,
  selectAvailableUserId,
} from "./authorization-selection";

describe("authorization selection", () => {
  it("resets an unavailable user to the current user", () => {
    expect(
      selectAvailableUserId(
        "removed-user",
        "current-user",
        ["other-user"],
        true,
      ),
    ).toBe("current-user");
  });

  it("does not retain another user when evaluating others is unavailable", () => {
    expect(
      selectAvailableUserId(
        "other-user",
        "current-user",
        ["other-user"],
        false,
      ),
    ).toBe("current-user");
  });

  it("keeps a valid permission and falls back when it is removed", () => {
    expect(
      selectAvailablePermission("tasks.read", ["users.read", "tasks.read"]),
    ).toBe("tasks.read");
    expect(
      selectAvailablePermission("tasks.read", ["users.read"]),
    ).toBe("users.read");
    expect(selectAvailablePermission("tasks.read", [])).toBe("");
  });
});
