<script setup lang="ts">
import { computed, ref } from "vue";
import NotificationList from "../components/dashboard/NotificationList.vue";
import StatCard from "../components/dashboard/StatCard.vue";
import TaskTable from "../components/dashboard/TaskTable.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { usePortalNotifications, usePortalShellState } from "../composables/portal-context";
import {
  mockDashboardNotifications,
  mockDashboardTasks,
} from "../mocks/dashboard";
import { createDashboardStats } from "../utils/dashboard-stats";
import type { DashboardNotification, DashboardTask } from "../types";

const { search } = usePortalShellState();
const portalNotifications = usePortalNotifications();

const taskFilter = ref<"all" | DashboardTask["status"]>("all");
const notifications = ref<DashboardNotification[]>(
  mockDashboardNotifications.map((item) => ({ ...item })),
);
const dashboardStats = createDashboardStats(mockDashboardTasks);

const filteredTasks = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase("zh-TW");
  return mockDashboardTasks.filter((task) => {
    const matchesFilter =
      taskFilter.value === "all" || task.status === taskFilter.value;
    const matchesSearch =
      !keyword ||
      task.name.toLocaleLowerCase("zh-TW").includes(keyword) ||
      task.client.toLocaleLowerCase("zh-TW").includes(keyword);
    return matchesFilter && matchesSearch;
  });
});

const currentDate = new Intl.DateTimeFormat("zh-TW", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "long",
}).format(new Date());

function markNotificationRead(id: number): void {
  const notification = notifications.value.find((item) => item.id === id);
  if (notification) notification.unread = false;
}

function unavailable(label: string): void {
  portalNotifications.notify(`${label}尚未開放，待 API 完成後提供。`, "warning");
}
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>總覽</h1>
        <p>{{ currentDate }} · 8 個客戶 · {{ mockDashboardTasks.length }} 個任務</p>
      </div>
      <div class="page-actions">
        <button
          class="button button-secondary"
          type="button"
          @click="unavailable('繼續上次工作')"
        >
          繼續上次工作
        </button>
        <button
          class="button button-primary"
          type="button"
          @click="unavailable('新增客戶')"
        >
          <AppIcon name="plus" :size="16" />新增客戶
        </button>
        <button
          class="button button-secondary"
          type="button"
          @click="unavailable('新增任務')"
        >
          <AppIcon name="plus" :size="16" />新增任務
        </button>
      </div>
    </header>

    <div class="mock-notice">
      <AppIcon name="activity" :size="17" />
      總覽、任務與通知目前使用暫時假資料，待 SEO API 完成後串接。
    </div>

    <div class="stat-grid">
      <StatCard
        v-for="stat in dashboardStats"
        :key="stat.label"
        :label="stat.label"
        :value="stat.value"
        :metrics="stat.metrics"
        :tone="stat.tone"
        :icon="stat.icon"
      />
    </div>

    <div class="dashboard-grid">
      <article class="card dashboard-tasks">
        <header class="card-header">
          <h2>任務列表</h2>
          <div class="filter-chips compact">
            <button
              :class="{ active: taskFilter === 'all' }"
              type="button"
              @click="taskFilter = 'all'"
            >
              全部
            </button>
            <button
              :class="{ active: taskFilter === 'progress' }"
              type="button"
              @click="taskFilter = 'progress'"
            >
              進行中
            </button>
            <button
              :class="{ active: taskFilter === 'waiting' }"
              type="button"
              @click="taskFilter = 'waiting'"
            >
              等待
            </button>
          </div>
        </header>
        <TaskTable
          :tasks="filteredTasks"
          @unavailable="unavailable"
        />
      </article>

      <div class="dashboard-aside">
        <article class="card">
          <header class="card-header">
            <h2>最新通知</h2>
            <button
              class="text-button"
              type="button"
              @click="unavailable('所有通知')"
            >
              查看全部
            </button>
          </header>
          <NotificationList
            :notifications="notifications"
            @read="markNotificationRead"
          />
        </article>

        <article class="card">
          <header class="card-header"><h2>快速操作</h2></header>
          <div class="quick-actions">
            <button type="button" @click="unavailable('新增任務')">
              <AppIcon name="briefcase" />新增任務
            </button>
            <button type="button" @click="unavailable('新增客戶')">
              <AppIcon name="users" />新增客戶
            </button>
            <button type="button" @click="unavailable('戰情室')">
              <AppIcon name="activity" />戰情室
            </button>
            <button type="button" @click="unavailable('策略分析')">
              <AppIcon name="sparkles" />策略分析
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
