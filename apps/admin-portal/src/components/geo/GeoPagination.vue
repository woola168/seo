<script setup lang="ts">
const props = defineProps<{
  page: number;
  perPage: number;
  total: number;
}>();

const emit = defineEmits<{
  "update:page": [page: number];
}>();

function setPage(page: number): void {
  const totalPages = Math.max(1, Math.ceil(props.total / props.perPage));
  emit("update:page", Math.min(Math.max(1, page), totalPages));
}
</script>

<template>
  <footer class="geo-pagination">
    <span>
      顯示 {{ total === 0 ? 0 : (page - 1) * perPage + 1 }}-{{ Math.min(page * perPage, total) }}，共 {{ total }} 筆
    </span>
    <div class="geo-pagination-pages">
      <button type="button" :disabled="page <= 1" @click="setPage(page - 1)">‹</button>
      <button
        v-for="item in Math.max(1, Math.ceil(total / perPage))"
        :key="item"
        type="button"
        :class="{ active: item === page }"
        @click="setPage(item)"
      >
        {{ item }}
      </button>
      <button type="button" :disabled="page >= Math.max(1, Math.ceil(total / perPage))" @click="setPage(page + 1)">›</button>
    </div>
  </footer>
</template>
