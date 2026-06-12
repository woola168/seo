<script setup lang="ts">
import type { DashboardNotification } from "../../types";

defineProps<{ notifications: DashboardNotification[] }>();
defineEmits<{ read: [id: number] }>();
</script>

<template>
  <div class="notification-list">
    <button
      v-for="notification in notifications"
      :key="notification.id"
      class="notification-item"
      :class="{ unread: notification.unread }"
      type="button"
      @click="$emit('read', notification.id)"
    >
      <span class="round-avatar" :style="{ background: notification.color }">
        {{ notification.initials }}
      </span>
      <span class="notification-copy">
        <strong>{{ notification.message }}</strong>
        <small>{{ notification.time }}</small>
      </span>
      <span v-if="notification.unread" class="unread-dot"></span>
    </button>
  </div>
</template>
