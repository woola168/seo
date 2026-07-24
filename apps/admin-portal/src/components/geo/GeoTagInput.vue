<script setup lang="ts">
import { ref } from "vue";
import AppIcon from "../ui/AppIcon.vue";

const props = defineProps<{ modelValue: string[]; placeholder?: string; invalid?: boolean }>();
const emit = defineEmits<{ "update:modelValue": [values: string[]] }>();
const draft = ref("");

function commit(): void {
  const additions = draft.value.split(/[,，]/).map((value) => value.trim()).filter(Boolean);
  if (additions.length) emit("update:modelValue", Array.from(new Set([...props.modelValue, ...additions])));
  draft.value = "";
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" || event.key === "," || event.key === "，") {
    event.preventDefault();
    commit();
  } else if (event.key === "Backspace" && !draft.value && props.modelValue.length) {
    emit("update:modelValue", props.modelValue.slice(0, -1));
  }
}
</script>

<template>
  <div class="geo-tag-input" :class="{ invalid }" @click="($event.currentTarget as HTMLElement).querySelector('input')?.focus()">
    <span v-for="(tag, index) in modelValue" :key="`${tag}-${index}`" class="geo-tag">
      {{ tag }}
      <button type="button" :aria-label="`移除 ${tag}`" @click.stop="$emit('update:modelValue', modelValue.filter((_, itemIndex) => itemIndex !== index))"><AppIcon name="x" :size="12" /></button>
    </span>
    <input v-model="draft" type="text" :placeholder="modelValue.length ? '' : placeholder" @blur="commit" @keydown="onKeydown" />
  </div>
</template>
