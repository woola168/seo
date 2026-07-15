<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps<{
  label: string;
  options: string[];
  selected: string[];
}>();

const emit = defineEmits<{
  "update:selected": [values: string[]];
}>();

const open = ref(false);
const buttonLabel = computed(() =>
  props.selected.length ? `${props.label} · ${props.selected.length}` : props.label,
);

function toggle(value: string): void {
  const next = props.selected.includes(value)
    ? props.selected.filter((item) => item !== value)
    : [...props.selected, value];
  emit("update:selected", next);
}
</script>

<template>
  <div class="geo-filter-dropdown">
    <button
      class="button button-secondary geo-filter-button"
      type="button"
      :aria-expanded="open"
      @click="open = !open"
    >
      {{ buttonLabel }}
    </button>
    <div v-if="open" class="geo-filter-menu">
      <label v-for="option in options" :key="option" class="geo-filter-option">
        <input
          type="checkbox"
          :checked="selected.includes(option)"
          @change="toggle(option)"
        />
        <span>{{ option }}</span>
      </label>
      <button
        v-if="selected.length"
        class="text-button"
        type="button"
        @click="emit('update:selected', [])"
      >
        清除 {{ label }}
      </button>
    </div>
  </div>
</template>
