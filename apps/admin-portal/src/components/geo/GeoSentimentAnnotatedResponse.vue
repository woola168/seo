<script setup lang="ts">
import { computed } from "vue";

import type { GeoRunResultSentimentFact } from "../../types";
import {
  buildEvidenceHighlights,
  filterOwnBrandSentiments,
  highlightEvidenceInHtml,
  renderSafeMarkdown,
} from "../../utils/geo-dashboard-drilldown";

const props = defineProps<{
  rawResponse: string;
  sentiments: GeoRunResultSentimentFact[];
}>();

const ownBrandSentiments = computed(() =>
  filterOwnBrandSentiments(props.sentiments),
);
const highlightedResponseHtml = computed(() =>
  highlightEvidenceInHtml(
    renderSafeMarkdown(props.rawResponse),
    buildEvidenceHighlights(props.rawResponse, ownBrandSentiments.value),
  ),
);

function confidenceLabel(confidence: number | null): string {
  return confidence === null ? "" : `信心 ${Math.round(confidence * 100)}%`;
}
</script>

<template>
  <article>
    <h3>AI 回答</h3>
    <div class="raw-response" v-html="highlightedResponseHtml"></div>
  </article>

  <article v-if="ownBrandSentiments.length" class="sentiment-annotations">
    <h3>情緒句標註</h3>
    <ul class="sentiment-evidence-list">
      <li
        v-for="(sentiment, index) in ownBrandSentiments"
        :key="`${sentiment.entityId}-${sentiment.sentiment}-${sentiment.statement}-${index}`"
      >
        <div class="sentiment-evidence-heading">
          <span :class="['sentiment-badge', `sentiment-badge-${sentiment.sentiment}`]">
            {{ sentiment.sentiment === "positive" ? "正向" : "負向" }}
          </span>
          <strong>{{ sentiment.entityName }}</strong>
          <span v-if="sentiment.theme" class="sentiment-theme">{{ sentiment.theme }}</span>
          <small v-if="sentiment.confidence !== null">{{ confidenceLabel(sentiment.confidence) }}</small>
        </div>
        <p class="sentiment-statement">{{ sentiment.statement }}</p>
      </li>
    </ul>
  </article>
</template>

<style scoped>
article {
  margin-top: 22px;
}

h3 {
  margin: 1em 0;
  font-size: 14px;
}

.raw-response {
  color: #434343;
  line-height: 1.75;
}

.raw-response :deep(:last-child) {
  margin-bottom: 0;
}

.raw-response :deep(.sentiment-highlight) {
  border-radius: 3px;
  padding: 1px 3px;
}

.raw-response :deep(.sentiment-highlight-positive) {
  background: #dcfce7;
  color: #166534;
}

.raw-response :deep(.sentiment-highlight-negative) {
  background: #fee2e2;
  color: #991b1b;
}

.sentiment-evidence-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.sentiment-evidence-list li {
  padding: 12px 14px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
}

.sentiment-evidence-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sentiment-evidence-heading strong {
  color: #262626;
  font-size: 13px;
}

.sentiment-evidence-heading small {
  margin-left: auto;
  color: #8c8c8c;
  font-size: 11px;
}

.sentiment-badge,
.sentiment-theme {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
}

.sentiment-badge-positive {
  background: #f6ffed;
  color: #237804;
}

.sentiment-badge-negative {
  background: #fff2f0;
  color: #a8071a;
}

.sentiment-theme {
  background: #f0f0f0;
  color: #595959;
}

.sentiment-statement {
  margin: 9px 0 0;
  color: #434343;
  font-size: 13px;
  line-height: 1.65;
}

@media (max-width: 639px) {
  .sentiment-evidence-heading small {
    width: 100%;
    margin-left: 0;
  }
}
</style>
