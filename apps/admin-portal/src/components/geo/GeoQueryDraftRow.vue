<script setup lang="ts">
import type { GeoQueryDraftResource } from "../../types";

const props = defineProps<{
  draft: GeoQueryDraftResource;
  selected: boolean;
  updating: boolean;
  intentLabel: string;
}>();
const emit = defineEmits<{
  toggle: [draft: GeoQueryDraftResource];
}>();
</script>

<template>
  <button
    class="geo-result-row"
    :class="{ selected, accepted: draft.acceptedQueryId }"
    type="button"
    :disabled="Boolean(draft.acceptedQueryId) || updating"
    @click="emit('toggle', props.draft)"
  >
    <input
      type="checkbox"
      :checked="selected"
      :disabled="Boolean(draft.acceptedQueryId) || updating"
      tabindex="-1"
    />
    <span class="geo-result-query">
      <strong>{{ draft.queryText }}</strong>
      <small>
        {{ draft.region }}/{{ draft.language }} · {{ intentLabel }}<template v-if="draft.acceptedQueryId"> · 已建立</template>
      </small>
    </span>
    <span class="geo-result-keywords">
      <span class="geo-result-mobile-label">Keywords</span>
      <span class="geo-result-keyword-list">
        <span
          v-for="(keyword, keywordIndex) in draft.keywords"
          :key="`${draft.id}-${keywordIndex}`"
          class="badge badge-muted"
        >
          {{ keyword }}
        </span>
        <small v-if="!draft.keywords.length">—</small>
      </span>
    </span>
  </button>
</template>
