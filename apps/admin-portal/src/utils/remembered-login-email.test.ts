import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getRememberedLoginEmail,
  updateRememberedLoginEmail,
} from "./remembered-login-email";

function createStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  };
}

describe("remembered login email", () => {
  beforeEach(() => vi.stubGlobal("localStorage", createStorage()));

  it("stores a trimmed email when remembering is enabled", () => {
    updateRememberedLoginEmail(" admin@example.com ", true);

    expect(getRememberedLoginEmail()).toBe("admin@example.com");
  });

  it("clears the previous email when remembering is disabled", () => {
    updateRememberedLoginEmail("admin@example.com", true);
    updateRememberedLoginEmail("other@example.com", false);

    expect(getRememberedLoginEmail()).toBe("");
  });

  it("does not store passwords or session tokens", () => {
    updateRememberedLoginEmail("admin@example.com", true);

    expect(localStorage.length).toBe(1);
    expect(localStorage.getItem("accessToken")).toBeNull();
    expect([...Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index))])
      .not.toContain("password");
  });

  it("does not fail when browser storage is unavailable", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    });

    expect(() => updateRememberedLoginEmail("admin@example.com", true)).not.toThrow();
    expect(getRememberedLoginEmail()).toBe("");
  });
});
