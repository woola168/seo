<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import PermissionGroupSelector from "../components/permissions/PermissionGroupSelector.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useAccessAdministration, usePortalSession } from "../composables/portal-context";
import { useRoleCreationForm } from "../composables/role-creation-form";
import { hasPermission } from "../utils/permissions";

const router = useRouter();
const session = usePortalSession();
const access = useAccessAdministration();
const { permissions, loading } = access;
const role = useRoleCreationForm();
const canCreate = computed(() =>
  hasPermission(session.capabilities.value?.permissions ?? [], "roles.manage"),
);

onMounted(() => void access.ensureView("role-creation"));

function submit(): void {
  if (!canCreate.value) return;
  role.submit((name, permissions, onSuccess) => {
    void access.createRole(name, permissions).then(async (created) => {
      if (!created) return;
      onSuccess();
      await router.replace({ name: "permissions-roles" });
    });
  });
}
</script>

<template>
  <section class="page role-creation-page">
    <button class="form-back" type="button" @click="router.replace({ name: 'permissions-roles' })">
      <AppIcon name="chevron-left" :size="14" />
      返回角色管理
    </button>

    <header class="page-header">
      <div>
        <h1>建立角色</h1>
        <p>設定角色名稱與可使用的功能權限。</p>
      </div>
    </header>

    <div v-if="!canCreate" class="card empty-state">
      <AppIcon name="lock" :size="32" />
      <strong>沒有建立角色的權限</strong>
      <span>需要 roles.manage 權限。</span>
    </div>

    <form v-else class="form-card" @submit.prevent="submit">
      <div class="form-card-inner">
        <label class="form-field">
          <span>角色名稱 *</span>
          <input
            v-model="role.roleName.value"
            required
            maxlength="120"
            placeholder="例如：Content Reviewer"
          />
        </label>

        <fieldset class="form-section">
          <legend>功能權限</legend>
          <p class="form-help">
            勾選功能群組後，系統會送出群組包含的細項 Permission。
          </p>
          <PermissionGroupSelector
            :permissions="permissions"
            :selected-permissions="role.selectedPermissions.value"
            :disabled="loading"
            @update:selected-permissions="role.selectedPermissions.value = $event"
          />
        </fieldset>

        <div class="form-actions">
          <button
            class="button button-secondary"
            type="button"
            @click="router.replace({ name: 'permissions-roles' })"
          >
            取消
          </button>
          <button
            class="button button-primary"
            type="submit"
            :disabled="loading || !role.roleName.value.trim()"
          >
            {{ loading ? "建立中..." : "建立角色" }}
          </button>
        </div>
      </div>
    </form>
  </section>
</template>
