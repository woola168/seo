<script setup lang="ts">
import { nextTick, ref } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import { parseGeoTagValues } from "../../utils/geo-tag-values";

defineProps<{ placeholder?: string; invalid?: boolean }>();
const model = defineModel<string[]>({ required: true });
const draft = ref("");
const composing = ref(false);
const commitAfterComposition = ref(false);

function appendTags(value: string): void {
  const additions = parseGeoTagValues(value);
  if (additions.length) model.value = Array.from(new Set([...model.value, ...additions]));
}

function commit(): void {
  if (composing.value) return;
  appendTags(draft.value);
  draft.value = "";
}

function onPaste(event: ClipboardEvent): void {
  const pastedText = event.clipboardData?.getData("text") ?? "";
  if (!/[\r\n,，]/.test(pastedText)) return;
  event.preventDefault();
  appendTags([draft.value, pastedText].filter(Boolean).join("\n"));
  draft.value = "";
}

function onKeydown(event: KeyboardEvent): void {
  if (event.isComposing || composing.value || event.keyCode === 229) {
    if (event.key === "Enter") commitAfterComposition.value = true;
    return;
  }
  if (event.key === "Enter" || event.key === "," || event.key === "，") {
    event.preventDefault();
    commit();
  } else if (event.key === "Backspace" && !draft.value && model.value.length) {
    model.value = model.value.slice(0, -1);
  }
}

function onCompositionStart(): void {
  composing.value = true;
  commitAfterComposition.value = false;
}

function onCompositionEnd(): void {
  composing.value = false;
  if (!commitAfterComposition.value) return;
  commitAfterComposition.value = false;
  void nextTick(commit);
}

function onBlur(): void {
  if (composing.value) {
    commitAfterComposition.value = true;
    return;
  }
  commit();
}
</script>

<template>
  <div class="geo-tag-input" :class="{ invalid }" @click="($event.currentTarget as HTMLElement).querySelector('input')?.focus()">
    <span v-for="(tag, index) in model" :key="`${tag}-${index}`" class="geo-tag">
      {{ tag }}
      <button type="button" :aria-label="`移除 ${tag}`" @click.stop="model = model.filter((_, itemIndex) => itemIndex !== index)"><AppIcon name="x" :size="12" /></button>
    </span>
    <input
      v-model="draft"
      type="text"
      :aria-invalid="Boolean(invalid)"
      :placeholder="model.length ? '' : placeholder"
      @blur="onBlur"
      @compositionstart="onCompositionStart"
      @compositionend="onCompositionEnd"
      @keydown="onKeydown"
      @paste="onPaste"
    />
  </div>
</template>
