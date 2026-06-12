<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import { mockDepartments } from "../../mocks/permissions";

defineEmits<{ unavailable: [label: string] }>();
</script>

<template>
  <div class="permission-content">
    <div class="mock-notice">
      <AppIcon name="activity" :size="17" />
      部門資料目前為暫時假資料，待部門管理 API 完成後串接。
    </div>
    <div class="department-grid">
      <article v-for="department in mockDepartments" :key="department.id" class="card">
        <div class="department-icon"><AppIcon name="users" :size="20" /></div>
        <h2>{{ department.name }}</h2>
        <p>{{ department.description }}</p>
        <span>{{ department.memberCount }} 位成員</span>
        <button
          class="button button-secondary"
          type="button"
          @click="$emit('unavailable', `${department.name}編輯`)"
        >
          管理部門
        </button>
      </article>
    </div>
  </div>
</template>
