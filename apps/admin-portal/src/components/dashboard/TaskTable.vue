<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import type { DashboardTask } from "../../types";

defineProps<{ tasks: DashboardTask[] }>();
defineEmits<{ unavailable: [label: string] }>();

const statusLabels = {
  progress: "進行中",
  waiting: "等待客戶",
  review: "審核中",
  pending: "待處理",
};
</script>

<template>
  <div class="table-scroll">
    <table class="data-table task-table">
      <thead>
        <tr>
          <th>任務／客戶</th>
          <th>狀態</th>
          <th>字數</th>
          <th>截止日</th>
          <th aria-label="操作"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.id">
          <td>
            <div class="identity-cell">
              <span class="round-avatar" :style="{ background: task.color }">
                {{ task.initials }}
              </span>
              <span>
                <strong>{{ task.name }}</strong>
                <small>{{ task.client }}</small>
              </span>
            </div>
          </td>
          <td>
            <span class="badge" :class="`badge-${task.status}`">
              {{ statusLabels[task.status] }}
            </span>
          </td>
          <td class="mono">{{ task.words.toLocaleString() }}</td>
          <td>{{ task.dueDate }}</td>
          <td>
            <button
              class="icon-button"
              type="button"
              aria-label="任務操作"
              @click="$emit('unavailable', `${task.name}操作`)"
            >
              <AppIcon name="more" :size="17" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
