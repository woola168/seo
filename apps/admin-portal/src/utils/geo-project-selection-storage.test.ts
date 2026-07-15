import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getStoredGeoProjectId,
  resolveStoredGeoProjectId,
  setStoredGeoProjectId,
} from "./geo-project-selection-storage";

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

describe("geo project selection storage", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", createStorage());
  });

  it("restores a stored project when it still exists", () => {
    setStoredGeoProjectId("project-b");

    expect(resolveStoredGeoProjectId([{ id: "project-a" }, { id: "project-b" }])).toBe(
      "project-b",
    );
  });

  it("falls back to the first project and updates storage", () => {
    setStoredGeoProjectId("removed-project");

    expect(resolveStoredGeoProjectId([{ id: "project-a" }, { id: "project-b" }])).toBe(
      "project-a",
    );
    expect(getStoredGeoProjectId()).toBe("project-a");
  });

  it("clears storage when there are no projects", () => {
    setStoredGeoProjectId("project-a");

    expect(resolveStoredGeoProjectId([])).toBe("");
    expect(getStoredGeoProjectId()).toBe("");
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

    expect(resolveStoredGeoProjectId([{ id: "project-a" }])).toBe("project-a");
  });
});
