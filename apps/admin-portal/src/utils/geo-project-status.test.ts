import { describe, expect, it, vi } from "vitest";

import {
  applyGeoProjectStatusResponse,
  geoProjectStatusAction,
  nextGeoProjectStatus,
  updateGeoProjectStatus,
} from "./geo-project-status";

describe("GEO Project status action", () => {
  it("pauses active Projects for the existing down action", () => {
    expect(nextGeoProjectStatus("active")).toBe("paused");
    expect(geoProjectStatusAction("active")).toBe("下架");
  });

  it.each(["paused", "archived"] as const)(
    "restores %s Projects to active",
    (status) => {
      expect(nextGeoProjectStatus(status)).toBe("active");
      expect(geoProjectStatusAction(status)).toBe("上架");
    },
  );

  it("updates only the matching row after a successful down action", async () => {
    const state = { updatingId: "" };
    const request = vi.fn().mockResolvedValue({
      projectId: "project-1",
      status: "paused",
      updatedAt: "2026-07-19T01:00:00Z",
    });

    const result = await updateGeoProjectStatus(state, project("active"), true, request);

    expect(request).toHaveBeenCalledWith("project-1", "paused");
    expect(state.updatingId).toBe("");
    expect(result.status).toBe("succeeded");
    if (result.status === "succeeded") {
      expect(applyGeoProjectStatusResponse(
        [project("active"), project("paused", "project-2")],
        result.response,
      )).toEqual([
        { ...project("active"), status: "paused", updatedAt: "2026-07-19T01:00:00Z" },
        project("paused", "project-2"),
      ]);
    }
  });

  it.each(["paused", "archived"] as const)(
    "sends active when restoring a %s Project",
    async (status) => {
      const request = vi.fn().mockResolvedValue({
        projectId: "project-1",
        status: "active",
        updatedAt: "2026-07-19T01:00:00Z",
      });

      await updateGeoProjectStatus({ updatingId: "" }, project(status), true, request);

      expect(request).toHaveBeenCalledWith("project-1", "active");
    },
  );

  it("does not send when permission is missing or another update is running", async () => {
    const request = vi.fn();

    await expect(updateGeoProjectStatus(
      { updatingId: "" },
      project("active"),
      false,
      request,
    )).resolves.toEqual({ status: "ignored" });
    await expect(updateGeoProjectStatus(
      { updatingId: "project-2" },
      project("active"),
      true,
      request,
    )).resolves.toEqual({ status: "ignored" });
    expect(request).not.toHaveBeenCalled();
  });

  it("keeps the global loading guard active until the request settles", async () => {
    const state = { updatingId: "" };
    let resolveRequest!: (value: {
      projectId: string;
      status: "paused";
      updatedAt: string;
    }) => void;
    const request = vi.fn().mockReturnValue(new Promise((resolve) => {
      resolveRequest = resolve;
    }));

    const pending = updateGeoProjectStatus(state, project("active"), true, request);

    expect(state.updatingId).toBe("project-1");
    await expect(updateGeoProjectStatus(
      state,
      project("paused", "project-2"),
      true,
      request,
    )).resolves.toEqual({ status: "ignored" });
    expect(request).toHaveBeenCalledTimes(1);

    resolveRequest({
      projectId: "project-1",
      status: "paused",
      updatedAt: "2026-07-19T01:00:00Z",
    });
    await pending;
    expect(state.updatingId).toBe("");
  });

  it("preserves row data and releases the guard when the request fails", async () => {
    const state = { updatingId: "" };
    const failure = new Error("status unavailable");

    const result = await updateGeoProjectStatus(
      state,
      project("active"),
      true,
      vi.fn().mockRejectedValue(failure),
    );

    expect(result).toEqual({ status: "failed", error: failure });
    expect(state.updatingId).toBe("");
  });
});

function project(
  status: "active" | "paused" | "archived",
  id = "project-1",
) {
  return {
    id,
    customerId: "customer-1",
    customerName: "範例客戶",
    name: "範例 Project",
    defaultRegion: "TW",
    defaultLanguage: "zh-TW",
    status,
    dailyRunBudget: 200,
    createdAt: "2026-07-19T00:00:00Z",
    updatedAt: "2026-07-19T00:00:00Z",
  };
}
