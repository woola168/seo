<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";

defineProps<{
  open: boolean;
  title: string;
  description?: string;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <div
    v-if="open"
    class="geo-drawer-backdrop"
    @click.self="emit('close')"
    @keydown.esc.prevent="emit('close')"
  >
    <aside class="geo-action-drawer" role="dialog" aria-modal="true">
      <header class="geo-drawer-header">
        <div>
          <h2>{{ title }}</h2>
          <p v-if="description">{{ description }}</p>
        </div>
        <button class="icon-button" type="button" aria-label="關閉" @click="emit('close')">
          <AppIcon name="x" :size="18" />
        </button>
      </header>
      <div class="geo-drawer-body">
        <slot />
      </div>
    </aside>
  </div>
</template>
