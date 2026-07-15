<script setup lang="ts">
defineProps<{
  label: string;
  required?: boolean;
  error?: string;
  full?: boolean;
}>();
</script>

<template>
  <label class="geo-form-field" :class="{ invalid: Boolean(error), full }">
    <span>
      {{ label }}
      <em v-if="required">*</em>
    </span>
    <slot />
    <small v-if="error" class="form-error">{{ error }}</small>
  </label>
</template>
