<script setup lang="ts">
import type { GeoProjectQueryIntentForm } from "../../services/geo-project-query-settings";

const props = defineProps<{
  modelValue: GeoProjectQueryIntentForm[];
  error?: string;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: GeoProjectQueryIntentForm[]];
  change: [];
}>();

function updateIntent(
  category: string,
  patch: Partial<Pick<GeoProjectQueryIntentForm, "selected" | "description">>,
): void {
  emit(
    "update:modelValue",
    props.modelValue.map((intent) =>
      intent.category === category ? { ...intent, ...patch } : intent,
    ),
  );
  emit("change");
}
</script>

<template>
  <div class="geo-intent-selector" :class="{ invalid: Boolean(error) }">
    <div v-for="intent in modelValue" :key="intent.category" class="geo-intent-option">
      <label class="geo-intent-choice">
        <input
          type="checkbox"
          :checked="intent.selected"
          @change="updateIntent(intent.category, { selected: ($event.target as HTMLInputElement).checked })"
        />
        <strong>{{ intent.label }}</strong>
      </label>
      <input
        type="text"
        :value="intent.description"
        :disabled="!intent.selected"
        :aria-label="`${intent.label} Intent 描述`"
        @input="updateIntent(intent.category, { description: ($event.target as HTMLInputElement).value })"
      />
    </div>
    <small v-if="error" class="form-error">{{ error }}</small>
  </div>
</template>
