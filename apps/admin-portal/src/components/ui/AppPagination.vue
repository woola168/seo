<script setup lang="ts">
import AppIcon from "./AppIcon.vue";

defineProps<{
  page: number;
  totalPages: number;
  total: number;
}>();

defineEmits<{ change: [page: number] }>();
</script>

<template>
  <div class="pagination">
    <span class="pagination-info">共 {{ total }} 筆</span>
    <div class="pagination-pages">
      <button
        type="button"
        :disabled="page <= 1"
        aria-label="上一頁"
        @click="$emit('change', page - 1)"
      >
        <AppIcon name="chevron-left" :size="16" />
      </button>
      <button
        v-for="item in totalPages"
        :key="item"
        type="button"
        :class="{ active: item === page }"
        @click="$emit('change', item)"
      >
        {{ item }}
      </button>
      <button
        type="button"
        :disabled="page >= totalPages"
        aria-label="下一頁"
        @click="$emit('change', page + 1)"
      >
        <AppIcon name="chevron-right" :size="16" />
      </button>
    </div>
  </div>
</template>
