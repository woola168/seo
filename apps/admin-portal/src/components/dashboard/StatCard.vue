<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import type { IconName } from "../../types";

defineProps<{
  label: string;
  value: string | number;
  detail: string;
  tone: "blue" | "amber" | "red" | "green";
  icon: IconName;
}>();
</script>

<template>
  <article class="stat-card" :class="`stat-${tone}`">
    <div class="stat-card-heading">
      <span>{{ label }}</span>
      <span class="stat-icon"><AppIcon :name="icon" :size="18" /></span>
    </div>
    <strong>{{ value }}</strong>
    <small>{{ detail }}</small>
  </article>
</template>
