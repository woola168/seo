import type {
  DashboardTask,
  IconName,
  SemanticTone,
  StatMetric,
} from "../types";

export interface DashboardStat {
  label: string;
  value: string | number;
  tone: Extract<SemanticTone, "info" | "warning" | "error" | "success">;
  icon: IconName;
  metrics: StatMetric[];
}

export function createDashboardStats(
  tasks: DashboardTask[],
): DashboardStat[] {
  const progressCount = tasks.filter(
    (task) => task.status === "progress",
  ).length;
  const waitingCount = tasks.filter((task) => task.status === "waiting").length;

  return [
    {
      label: "全部任務",
      value: tasks.length,
      tone: "info",
      icon: "list",
      metrics: [
        { label: "進行中", value: progressCount, tone: "info" },
        { label: "已完成", value: 0, tone: "success" },
      ],
    },
    {
      label: "等待客戶",
      value: waitingCount,
      tone: "warning",
      icon: "clock",
      metrics: [{ label: "需催促", value: waitingCount }],
    },
    {
      label: "被退回",
      value: 0,
      tone: "error",
      icon: "alert-circle",
      metrics: [{ label: "需修正", value: 0 }],
    },
    {
      label: "本月完成",
      value: 0,
      tone: "success",
      icon: "check-circle",
      metrics: [{ label: "目標", value: 20 }],
    },
  ];
}
