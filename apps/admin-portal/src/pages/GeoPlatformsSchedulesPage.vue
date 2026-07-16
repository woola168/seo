<script setup lang="ts">
import { computed, onMounted } from "vue";
import GeoPageHeader from "../components/geo/GeoPageHeader.vue";
import GeoStatusBadge from "../components/geo/GeoStatusBadge.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useGeoProjectWorkspace } from "../composables/geo-project-workspace";

const workspace = useGeoProjectWorkspace("platforms-schedules");

const platformSummaries = computed(() =>
  workspace.platforms.value.map((platform) => ({
    ...platform,
    scheduledQueryCount:
      platform.status === "active"
        ? workspace.queries.value.filter((query) => query.status === "active").length
        : 0,
  })),
);

onMounted(() => {
  void workspace.loadProjects();
});
</script>

<template>
  <section class="page geo-page geo-kinsan-page">
    <GeoPageHeader
      title="Platforms"
      description="每日固定於 Asia/Taipei 03:00 執行 active Query × active Platform。"
      :projects="workspace.projects.value"
      :selected-project-id="workspace.selectedProjectId.value"
      :loading="workspace.loading.value"
      @update:selected-project-id="workspace.selectedProjectId.value = $event"
      @refresh="workspace.loadProjects"
    />
    <div v-if="workspace.usingMockData.value" class="mock-notice subtle">
      <AppIcon name="alert-circle" :size="17" />API 無法使用，目前顯示示意資料。
    </div>
    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <div v-if="workspace.loading.value && !workspace.selectedProject.value" class="empty-state">正在載入 GEO 資料</div>
    <div v-else-if="!workspace.selectedProject.value" class="empty-state">請先建立 GEO project。</div>

    <template v-else>
      <div class="mock-notice subtle">
        排程時間由系統統一管理；此頁不再提供個別 query 的 schedule 設定。
      </div>
      <div class="geo-platform-grid">
        <article v-for="platform in platformSummaries" :key="platform.id" class="card geo-platform-card">
          <strong>{{ platform.name }}</strong>
          <span>{{ platform.model }}</span>
          <small>{{ platform.scheduledQueryCount }} active queries scheduled</small>
          <GeoStatusBadge :value="platform.status" />
        </article>
      </div>
    </template>
  </section>
</template>
