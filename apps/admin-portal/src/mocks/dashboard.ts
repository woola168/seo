import type {
  DashboardNotification,
  DashboardTask,
} from "../types";

// TODO(API): Replace these records when dashboard, task and notification APIs exist.
export const mockDashboardTasks: DashboardTask[] = [
  {
    id: 1,
    name: "Q2 SEO 落地頁優化",
    client: "ACME Corp",
    initials: "AC",
    color: "#1677ff",
    status: "progress",
    words: 2400,
    dueDate: "06/15",
  },
  {
    id: 2,
    name: "品牌故事文章",
    client: "NexGen Bio",
    initials: "NB",
    color: "#52c41a",
    status: "progress",
    words: 800,
    dueDate: "06/18",
  },
  {
    id: 3,
    name: "電商首頁改寫",
    client: "ShopPlus",
    initials: "SP",
    color: "#8b5cf6",
    status: "waiting",
    words: 1200,
    dueDate: "06/20",
  },
  {
    id: 4,
    name: "月報關鍵字分析",
    client: "ACME Corp",
    initials: "AC",
    color: "#1677ff",
    status: "progress",
    words: 600,
    dueDate: "06/22",
  },
  {
    id: 5,
    name: "產品頁 A/B 文案",
    client: "Volta Tech",
    initials: "VT",
    color: "#d68c24",
    status: "review",
    words: 980,
    dueDate: "06/25",
  },
];

export const mockDashboardNotifications: DashboardNotification[] = [
  {
    id: 1,
    initials: "AC",
    color: "#1677ff",
    message: "ACME Corp 對「Q2 SEO 落地頁」留下評論",
    time: "10 分鐘前",
    unread: true,
  },
  {
    id: 2,
    initials: "NB",
    color: "#52c41a",
    message: "NexGen Bio 的品牌故事文案已完成",
    time: "1 小時前",
    unread: true,
  },
  {
    id: 3,
    initials: "SP",
    color: "#8b5cf6",
    message: "ShopPlus 退回電商首頁改寫，等待修正",
    time: "3 小時前",
    unread: false,
  },
];
