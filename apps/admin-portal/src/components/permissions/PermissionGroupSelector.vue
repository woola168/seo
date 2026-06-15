<script setup lang="ts">
import { computed } from "vue";
import {
  buildPermissionGroups,
  permissionGroupState,
  togglePermissionGroup,
} from "../../utils/permission-groups";
import { describePermission } from "../../utils/permissions";

const props = defineProps<{
  permissions: string[];
  selectedPermissions: string[];
  disabled: boolean;
}>();

const emit = defineEmits<{
  "update:selected-permissions": [permissions: string[]];
}>();

const groups = computed(() => buildPermissionGroups(props.permissions));

function state(groupPermissions: string[]) {
  return permissionGroupState(props.selectedPermissions, groupPermissions);
}

function toggle(groupPermissions: string[]): void {
  emit(
    "update:selected-permissions",
    togglePermissionGroup(props.selectedPermissions, groupPermissions),
  );
}
</script>

<template>
  <div class="permission-group-list">
    <article
      v-for="group in groups"
      :key="group.id"
      class="permission-group"
      :class="{ partial: state(group.permissions) === 'partial' }"
    >
      <label class="permission-group-main">
        <input
          type="checkbox"
          :checked="state(group.permissions) === 'all'"
          :indeterminate="state(group.permissions) === 'partial'"
          :disabled="disabled"
          @change="toggle(group.permissions)"
        />
        <span>
          <strong>{{ group.label }}</strong>
          <small>{{ group.description }}</small>
          <em v-if="state(group.permissions) === 'partial'">部分開放</em>
        </span>
      </label>

      <!-- <details class="permission-group-details">
        <summary>查看包含功能（{{ group.permissions.length }}）</summary>
        <ul>
          <li v-for="permission in group.permissions" :key="permission">
            <span>{{ describePermission(permission).label }}</span>
            <code>{{ permission }}</code>
          </li>
        </ul>
      </details> -->
    </article>
  </div>
</template>
