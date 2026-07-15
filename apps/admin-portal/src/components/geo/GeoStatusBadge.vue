<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  value: string | null | undefined;
}>();

const badgeClass = computed(() => {
  if (["active", "succeeded", "completed", "positive", "own_brand"].includes(props.value ?? "")) {
    return "badge badge-success";
  }
  if (
    ["paused", "pending", "published", "running_external", "running", "neutral", "competitor"].includes(
      props.value ?? "",
    )
  ) {
    return "badge badge-warning";
  }
  if (["failed", "cancelled", "negative", "archived", "high"].includes(props.value ?? "")) {
    return "badge badge-error";
  }
  if (props.value === "normal") return "badge badge-info";
  return "badge badge-muted";
});
</script>

<template>
  <span :class="badgeClass">{{ value ?? "-" }}</span>
</template>
