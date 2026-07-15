<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import GeoActionDrawer from "../components/geo/GeoActionDrawer.vue";
import GeoFilterDropdown from "../components/geo/GeoFilterDropdown.vue";
import GeoFormField from "../components/geo/GeoFormField.vue";
import GeoPageHeader from "../components/geo/GeoPageHeader.vue";
import GeoPagination from "../components/geo/GeoPagination.vue";
import GeoStatusBadge from "../components/geo/GeoStatusBadge.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useGeoFormErrors, type GeoFormValidationError } from "../composables/geo-form-errors";
import { useGeoProjectWorkspace } from "../composables/geo-project-workspace";
import { api } from "../services/api";
import type { GeoEntity } from "../types";

const workspace = useGeoProjectWorkspace("entities");
const { formErrors, setFormErrors, clearFieldError, clearFormErrors } = useGeoFormErrors();
const search = ref("");
const drawerOpen = ref(false);
const page = ref(1);
const perPage = 10;
const typeFilters = ref<string[]>([]);
const statusFilters = ref<string[]>([]);
const form = reactive({
  entityType: "own_brand" as GeoEntity["entityType"],
  name: "",
  alias: "",
  websiteUrl: "",
  description: "",
});

const filteredEntities = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return workspace.entities.value.filter((entity) => {
    const aliases = getAliases(entity.id);
    const matchesKeyword =
      !keyword ||
      [entity.name, aliases, entity.websiteUrl ?? ""].join(" ").toLowerCase().includes(keyword);
    return (
      matchesKeyword &&
      (!typeFilters.value.length || typeFilters.value.includes(entity.entityType)) &&
      (!statusFilters.value.length || statusFilters.value.includes(entity.status))
    );
  });
});
const activeFilterCount = computed(() => typeFilters.value.length + statusFilters.value.length);
const pageRows = computed(() => filteredEntities.value.slice((page.value - 1) * perPage, page.value * perPage));

onMounted(() => {
  void workspace.loadProjects();
});

function getAliases(entityId: string): string {
  const values = workspace.aliases.value
    .filter((alias) => alias.entityId === entityId)
    .map((alias) => alias.alias);
  return values.length ? values.join(", ") : "-";
}

function openCreate(): void {
  form.entityType = "own_brand";
  form.name = "";
  form.alias = "";
  form.websiteUrl = "";
  form.description = "";
  clearFormErrors();
  drawerOpen.value = true;
}

function closeDrawer(): void {
  drawerOpen.value = false;
  clearFormErrors();
}

function validate(): boolean {
  const errors: GeoFormValidationError[] = [];
  if (!form.entityType) errors.push({ field: "entityType", message: "請選擇 Type。" });
  if (!form.name.trim()) errors.push({ field: "name", message: "請輸入 Entity 名稱。" });
  return setFormErrors(errors);
}

async function submit(): Promise<void> {
  if (!validate()) return;
  const project = workspace.selectedProject.value;
  if (!project) return;
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const entity = await api.geoAnalysis.createEntity(project.id, {
      entityType: form.entityType,
      name: form.name.trim(),
      websiteUrl: form.websiteUrl.trim() || null,
      description: form.description.trim(),
      status: "active",
    });
    workspace.entities.value.unshift(entity);
    if (form.alias.trim()) {
      workspace.aliases.value.unshift(
        await api.geoAnalysis.createAlias(entity.id, {
          alias: form.alias.trim(),
          matchType: "contains",
        }),
      );
    }
    workspace.setMessage("已建立 entity。");
    closeDrawer();
  });
}

async function deleteEntity(entityId: string): Promise<void> {
  await workspace.runAction(async () => {
    if (!workspace.usingMockData.value) await api.geoAnalysis.deleteEntity(entityId);
    workspace.entities.value = workspace.entities.value.filter((entity) => entity.id !== entityId);
    workspace.aliases.value = workspace.aliases.value.filter((alias) => alias.entityId !== entityId);
    workspace.setMessage("已刪除 entity。");
  });
}

function clearFilters(): void {
  search.value = "";
  typeFilters.value = [];
  statusFilters.value = [];
  page.value = 1;
}
</script>

<template>
  <section class="page geo-page geo-kinsan-page">
    <GeoPageHeader
      title="Entities & Aliases"
      description="管理品牌、競品與別名辨識規則。"
      :projects="workspace.projects.value"
      :selected-project-id="workspace.selectedProjectId.value"
      :loading="workspace.loading.value"
      action-label="新增 Entity"
      @update:selected-project-id="workspace.selectedProjectId.value = $event"
      @refresh="workspace.loadProjects"
      @action="openCreate"
    />
    <div v-if="workspace.usingMockData.value" class="mock-notice subtle"><AppIcon name="alert-circle" :size="17" />API 無法使用，目前顯示示意資料。</div>
    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <div class="geo-local-message">{{ workspace.localMessage.value }}</div>
    <div v-if="workspace.loading.value && !workspace.selectedProject.value" class="empty-state">正在載入 GEO 資料</div>
    <div v-else-if="!workspace.selectedProject.value" class="empty-state">請先建立 GEO project。</div>

    <article v-else class="card geo-kinsan-card">
      <header class="geo-kinsan-card-header">
        <strong>Entity List</strong>
        <span>共 {{ workspace.entities.value.length }} 筆</span>
      </header>
      <div class="geo-kinsan-toolbar">
        <label class="geo-search-field"><AppIcon name="search" :size="16" /><input v-model="search" type="search" placeholder="搜尋名稱、別名、網址…" @input="page = 1" /></label>
        <GeoFilterDropdown label="Type" :options="['own_brand', 'brand', 'competitor', 'website', 'partner']" :selected="typeFilters" @update:selected="typeFilters = $event; page = 1" />
        <GeoFilterDropdown label="Status" :options="['active', 'paused', 'archived']" :selected="statusFilters" @update:selected="statusFilters = $event; page = 1" />
        <span v-if="activeFilterCount || search" class="geo-clear-filters" @click="clearFilters">清除全部</span>
      </div>
      <div class="geo-kinsan-table-wrap">
        <table class="data-table geo-table geo-kinsan-table">
          <thead><tr><th>Name</th><th>Type</th><th>Aliases</th><th>Website</th><th>Status</th><th class="sticky-action">Actions</th></tr></thead>
          <tbody>
            <tr v-for="entity in pageRows" :key="entity.id">
              <td><strong>{{ entity.name }}</strong><small>{{ entity.description || "-" }}</small></td>
              <td><GeoStatusBadge :value="entity.entityType" /></td>
              <td>{{ getAliases(entity.id) }}</td>
              <td>{{ entity.websiteUrl ?? "-" }}</td>
              <td><GeoStatusBadge :value="entity.status" /></td>
              <td class="sticky-action">
                <div class="geo-row-actions">
                  <button class="geo-row-action danger" type="button" title="刪除" @click="deleteEntity(entity.id)">
                    <AppIcon name="trash" :size="14" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredEntities.length === 0"><td class="geo-table-empty" colspan="6">找不到符合條件的 entity。</td></tr>
          </tbody>
        </table>
      </div>
      <GeoPagination v-model:page="page" :per-page="perPage" :total="filteredEntities.length" />
    </article>

    <GeoActionDrawer :open="drawerOpen" title="建立 Entity" description="新增品牌、競品或網站 entity。" @close="closeDrawer">
      <form class="geo-drawer-form" @submit.prevent="submit">
        <GeoFormField label="Type" required :error="formErrors.entityType"><select v-model="form.entityType" :class="{ invalid: formErrors.entityType }" @change="clearFieldError('entityType')"><option value="own_brand">own_brand</option><option value="brand">brand</option><option value="competitor">competitor</option><option value="website">website</option><option value="partner">partner</option></select></GeoFormField>
        <GeoFormField label="名稱" required :error="formErrors.name"><input v-model="form.name" type="text" :class="{ invalid: formErrors.name }" placeholder="品牌或競品名稱" @input="clearFieldError('name')" /></GeoFormField>
        <GeoFormField label="Alias"><input v-model="form.alias" type="text" placeholder="例如：金山溫泉旅宿, example.com" /></GeoFormField>
        <GeoFormField label="Website URL"><input v-model="form.websiteUrl" type="url" placeholder="https://example.com" /></GeoFormField>
        <GeoFormField label="描述" full><textarea v-model="form.description" rows="4" placeholder="追蹤目的或辨識規則"></textarea></GeoFormField>
        <div class="geo-drawer-actions"><button class="button button-secondary" type="button" @click="closeDrawer">取消</button><button class="button button-primary" type="submit" :disabled="workspace.actionLoading.value">建立 Entity</button></div>
      </form>
    </GeoActionDrawer>
  </section>
</template>
