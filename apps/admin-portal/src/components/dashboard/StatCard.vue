<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import type {
  IconName,
  SemanticTone,
  StatMetric,
} from "../../types";

defineProps<{
  label: string;
  value: string | number;
  metrics: StatMetric[];
  tone: Extract<SemanticTone, "info" | "warning" | "error" | "success">;
  icon: IconName;
}>();
</script>

<template>
  <article class="stat-card">
    <div class="stat-card-heading">
      <span class="stat-icon" :class="`tone-${tone}`">
        <AppIcon :name="icon" :size="18" />
      </span>
      <span>{{ label }}</span>
    </div>
    <strong>{{ value }}</strong>
    <div class="stat-metrics">
      <span v-for="metric in metrics" :key="metric.label">
        {{ metric.label }}
        <b :class="metric.tone ? `text-${metric.tone}` : undefined">
          {{ metric.value }}
        </b>
      </span>
    </div>
  </article>
</template>
