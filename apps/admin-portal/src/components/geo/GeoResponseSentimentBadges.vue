<script setup lang="ts">
defineProps<{
  positiveCount: number;
  negativeCount: number;
  analyzed: boolean;
}>();
</script>

<template>
  <span class="response-sentiment-badges">
    <span
      v-if="analyzed && positiveCount > 0"
      class="response-sentiment-badge positive"
      :title="`正向情緒 ${positiveCount} 句`"
    >
      正向
    </span>
    <span
      v-if="analyzed && negativeCount > 0"
      class="response-sentiment-badge negative"
      :title="`負向情緒 ${negativeCount} 句`"
    >
      負向
    </span>
    <span v-if="!analyzed" class="pending">待分析</span>
    <span
      v-else-if="positiveCount === 0 && negativeCount === 0"
      class="empty"
    >
      無
    </span>
  </span>
</template>

<style scoped>
.response-sentiment-badges {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.response-sentiment-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  line-height: 16px;
  white-space: nowrap;
}

.response-sentiment-badge.positive {
  background: #f6ffed;
  color: #237804;
}

.response-sentiment-badge.negative {
  background: #fff1f0;
  color: #cf1322;
}

.empty,
.pending {
  color: #8c8c8c;
  font-size: 12px;
}
</style>
