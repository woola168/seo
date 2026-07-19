<script setup lang="ts">
defineProps<{
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  single?: boolean;
}>();
defineEmits<{ cancel: []; confirm: [] }>();
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="geo-dialog-backdrop" role="presentation" @click.self="$emit('cancel')">
      <section class="geo-dialog" :class="{ 'is-single': single }" role="dialog" aria-modal="true" :aria-label="title">
        <header><strong>{{ title }}</strong><button v-if="!single" type="button" aria-label="關閉" @click="$emit('cancel')">×</button></header>
        <p>{{ message }}</p>
        <footer>
          <button v-if="!single" class="button button-secondary" type="button" @click="$emit('cancel')">取消</button>
          <button class="button button-primary" type="button" @click="$emit('confirm')">{{ confirmLabel ?? '確定' }}</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
