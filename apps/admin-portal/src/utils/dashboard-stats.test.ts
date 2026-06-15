import { describe, expect, it } from "vitest";

import { mockDashboardTasks } from "../mocks/dashboard";
import { createDashboardStats } from "./dashboard-stats";

describe("dashboard stats", () => {
  it("uses the reference icons and semantic tones", () => {
    const stats = createDashboardStats(mockDashboardTasks);

    expect(stats.map(({ icon, tone }) => ({ icon, tone }))).toEqual([
      { icon: "list", tone: "info" },
      { icon: "clock", tone: "warning" },
      { icon: "alert-circle", tone: "error" },
      { icon: "check-circle", tone: "success" },
    ]);
  });

  it("provides structured metrics with semantic value tones", () => {
    const [allTasks, waiting] = createDashboardStats(mockDashboardTasks);

    expect(allTasks?.metrics).toEqual([
      { label: "進行中", value: 3, tone: "info" },
      { label: "已完成", value: 0, tone: "success" },
    ]);
    expect(waiting?.metrics).toEqual([
      { label: "需催促", value: 1 },
    ]);
  });
});
