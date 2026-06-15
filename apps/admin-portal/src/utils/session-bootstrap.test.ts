import { describe, expect, it } from "vitest";

import { shouldRestoreSession } from "./session-bootstrap";

describe("shouldRestoreSession", () => {
  it("restores an existing session before rendering the login page", () => {
    expect(shouldRestoreSession(null, true)).toBe(true);
  });

  it("shows the login page immediately when there is no session", () => {
    expect(shouldRestoreSession(null, false)).toBe(false);
  });

  it("does not restore a session while account recovery is active", () => {
    expect(shouldRestoreSession("reset", true)).toBe(false);
  });
});
