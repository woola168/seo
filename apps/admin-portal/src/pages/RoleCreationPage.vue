<script setup lang="ts">
import { computed } from "vue";
import PermissionGroupSelector from "../components/permissions/PermissionGroupSelector.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useRoleCreationForm } from "../composables/role-creation-form";
import type { Capabilities } from "../types";
import { hasPermission } from "../utils/permissions";

const props = defineProps<{
  capabilities: Capabilities;
  permissions: string[];
  loading: boolean;
}>();

const emit = defineEmits<{
  back: [];
  submit: [
    name: string,
    permissions: string[],
    onSuccess: () => void,
  ];
}>();

const role = useRoleCreationForm();
const canCreate = computed(() =>
  hasPermission(props.capabilities.permissions, "roles.manage"),
);

function submit(): void {
  if (!canCreate.value) return;
  role.submit((name, permissions, onSuccess) => {
    emit("submit", name, permissions, () => {
      onSuccess();
      emit("back");
    });
  });
}
</script>

<template>
  <section class="page role-creation-page">
    <button class="form-back" type="button" @click="$emit('back')">
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
            @click="$emit('back')"
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
