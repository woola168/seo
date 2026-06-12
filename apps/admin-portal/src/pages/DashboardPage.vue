<script setup lang="ts">
import { computed, ref } from "vue";
import NotificationList from "../components/dashboard/NotificationList.vue";
import StatCard from "../components/dashboard/StatCard.vue";
import TaskTable from "../components/dashboard/TaskTable.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import {
  mockDashboardNotifications,
  mockDashboardTasks,
} from "../mocks/dashboard";
import type {
  Capabilities,
  DashboardNotification,
  DashboardTask,
} from "../types";

const props = defineProps<{
  capabilities: Capabilities;
  search: string;
}>();

defineEmits<{ unavailable: [label: string] }>();

const taskFilter = ref<"all" | DashboardTask["status"]>("all");
const notifications = ref<DashboardNotification[]>(
  mockDashboardNotifications.map((item) => ({ ...item })),
);

const filteredTasks = computed(() => {
  const search = props.search.trim().toLocaleLowerCase("zh-TW");
  return mockDashboardTasks.filter((task) => {
    const matchesFilter =
      taskFilter.value === "all" || task.status === taskFilter.value;
    const matchesSearch =
      !search ||
      task.name.toLocaleLowerCase("zh-TW").includes(search) ||
      task.client.toLocaleLowerCase("zh-TW").includes(search);
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
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <p class="page-kicker">儀表板</p>
        <h1>總覽</h1>
        <p>{{ currentDate }} · 暫用展示資料</p>
      </div>
      <div class="page-actions">
        <button
          class="button button-secondary"
          type="button"
          @click="$emit('unavailable', '匯出報表')"
        >
          <AppIcon name="download" :size="17" />匯出報表
        </button>
        <button
          class="button button-secondary"
          type="button"
          @click="$emit('unavailable', '新增客戶')"
        >
          <AppIcon name="users" :size="17" />新增客戶
        </button>
        <button
          class="button button-primary"
          type="button"
          @click="$emit('unavailable', '新增任務')"
        >
          <AppIcon name="plus" :size="17" />新增任務
        </button>
      </div>
    </header>

    <div class="mock-notice">
      <AppIcon name="activity" :size="17" />
      總覽、任務與通知目前使用暫時假資料，待 SEO API 完成後串接。
    </div>

    <div class="filter-chips" aria-label="任務期間">
      <button class="active" type="button">
        <AppIcon name="layers" :size="15" />全部
      </button>
      <button type="button" @click="$emit('unavailable', '今日篩選')">
        今日
      </button>
      <button type="button" @click="$emit('unavailable', '本週篩選')">
        本週
      </button>
      <button type="button" @click="$emit('unavailable', '本月篩選')">
        本月
      </button>
    </div>

    <div class="stat-grid">
      <StatCard
        label="全部任務"
        :value="mockDashboardTasks.length"
        detail="進行中 3 · 已完成 0"
        tone="blue"
        icon="briefcase"
      />
      <StatCard
        label="等待客戶"
        :value="mockDashboardTasks.filter((task) => task.status === 'waiting').length"
        detail="需催促"
        tone="amber"
        icon="clock"
      />
      <StatCard
        label="可用權限"
        :value="capabilities.permissions.length"
        detail="由 access-control API 提供"
        tone="red"
        icon="shield"
      />
      <StatCard
        label="本月完成"
        value="0"
        detail="目標 10 · 達成 0%"
        tone="green"
        icon="check"
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
          @unavailable="$emit('unavailable', $event)"
        />
      </article>

      <div class="dashboard-aside">
        <article class="card">
          <header class="card-header">
            <h2>最新通知</h2>
            <button
              class="text-button"
              type="button"
              @click="$emit('unavailable', '所有通知')"
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
            <button type="button" @click="$emit('unavailable', '新增任務')">
              <AppIcon name="briefcase" />新增任務
            </button>
            <button type="button" @click="$emit('unavailable', '新增客戶')">
              <AppIcon name="users" />新增客戶
            </button>
            <button type="button" @click="$emit('unavailable', '戰情室')">
              <AppIcon name="activity" />戰情室
            </button>
            <button type="button" @click="$emit('unavailable', '策略分析')">
              <AppIcon name="sparkles" />策略分析
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
