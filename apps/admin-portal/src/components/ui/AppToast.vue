<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import type { ToastMessage } from "../../types";

defineProps<{ toast: ToastMessage }>();
defineEmits<{ close: [] }>();
</script>

<template>
  <div class="toast" :class="`toast-${toast.tone}`" role="status">
    <AppIcon :name="toast.tone === 'success' ? 'check' : 'bell'" :size="16" />
    <span>{{ toast.message }}</span>
    <button type="button" aria-label="關閉通知" @click="$emit('close')">
      <AppIcon name="x" :size="14" />
    </button>
  </div>
</template>
