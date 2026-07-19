<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import AppIcon from "../ui/AppIcon.vue";

const props = defineProps<{
  label: string;
  options: string[];
  selected: string[];
  optionLabels?: Record<string, string>;
  showSelectAll?: boolean;
  showChevron?: boolean;
  searchable?: boolean;
}>();

const emit = defineEmits<{
  "update:selected": [values: string[]];
}>();

const open = ref(false);
const query = ref("");
const root = ref<HTMLElement | null>(null);
const buttonLabel = computed(() =>
  props.selected.length ? `${props.label} · ${props.selected.length}` : props.label,
);
const filteredOptions = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return keyword
    ? props.options.filter((option) => (props.optionLabels?.[option] ?? option).toLowerCase().includes(keyword))
    : props.options;
});
const allSelected = computed(() => props.options.length > 0 && props.options.every((option) => props.selected.includes(option)));

onMounted(() => {
  document.addEventListener("click", closeFromOutside);
  window.addEventListener("scroll", closeFromScroll, true);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", closeFromOutside);
  window.removeEventListener("scroll", closeFromScroll, true);
});

function toggleMenu(): void {
  if (!open.value) query.value = "";
  open.value = !open.value;
}

function toggle(value: string): void {
  const next = props.selected.includes(value)
    ? props.selected.filter((item) => item !== value)
    : [...props.selected, value];
  emit("update:selected", next);
}

function toggleAll(): void {
  emit("update:selected", allSelected.value ? [] : [...props.options]);
}

function closeFromOutside(event: MouseEvent): void {
  if (open.value && !root.value?.contains(event.target as Node)) open.value = false;
}

function closeFromScroll(): void {
  open.value = false;
}
</script>

<template>
  <div ref="root" class="geo-filter-dropdown">
    <button
      class="button button-secondary geo-filter-button"
      :class="{ active: showChevron && (open || selected.length) }"
      type="button"
      :aria-expanded="open"
      @click="toggleMenu"
    >
      {{ buttonLabel }}
      <AppIcon v-if="showChevron" class="geo-filter-chevron" name="chevron-right" :size="13" />
    </button>
    <div v-if="open" class="geo-filter-menu">
      <label v-if="searchable && options.length >= 8" class="geo-filter-search">
        <AppIcon name="search" :size="12" />
        <input v-model="query" type="search" :placeholder="`搜尋 ${label}…`" />
      </label>
      <button
        v-if="showSelectAll && options.length >= 3 && !query"
        class="geo-filter-select-all"
        type="button"
        @click="toggleAll"
      >
        {{ allSelected ? "取消全選" : "全選" }}
      </button>
      <div class="geo-filter-options">
        <label v-for="option in filteredOptions" :key="option" class="geo-filter-option">
          <input
            :class="{ 'is-custom': showChevron }"
            type="checkbox"
            :checked="selected.includes(option)"
            @change="toggle(option)"
          />
          <span v-if="showChevron" class="geo-filter-checkbox"><AppIcon v-if="selected.includes(option)" name="check" :size="11" /></span>
          <span>{{ optionLabels?.[option] ?? option }}</span>
        </label>
        <div v-if="!filteredOptions.length" class="geo-filter-empty">找不到相符項目</div>
      </div>
      <button
        v-if="selected.length && !showSelectAll"
        class="text-button"
        type="button"
        @click="emit('update:selected', [])"
      >
        清除 {{ label }}
      </button>
    </div>
  </div>
</template>
