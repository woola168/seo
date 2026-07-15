<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import type { GeoProject } from "../../types";

defineProps<{
  title: string;
  description: string;
  projects: GeoProject[];
  selectedProjectId: string;
  loading: boolean;
  actionLabel?: string;
}>();

const emit = defineEmits<{
  "update:selected-project-id": [projectId: string];
  refresh: [];
  action: [];
}>();
</script>

<template>
  <header class="page-header geo-kinsan-header">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div class="page-actions geo-kinsan-header-actions">
      <button v-if="actionLabel" class="button button-primary" type="button" @click="emit('action')">
        <AppIcon name="plus" :size="14" />{{ actionLabel }}
      </button>
    </div>
  </header>
</template>
