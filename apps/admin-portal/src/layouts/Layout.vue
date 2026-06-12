<script setup lang="ts">
import AppIcon from "../components/ui/AppIcon.vue";
import type {
  NavigationItem,
  PageId,
  SessionUser,
} from "../types";

defineProps<{
  user: SessionUser;
  activePage: PageId;
  navigation: NavigationItem[];
  collapsed: boolean;
  search: string;
}>();

defineEmits<{
  navigate: [page: PageId];
  logout: [];
  refresh: [];
  "toggle-sidebar": [];
  "update:search": [value: string];
  unavailable: [label: string];
}>();
</script>

<template>
  <div class="layout" :class="{ 'layout-collapsed': collapsed }">
    <aside class="layout-sidebar">
      <div class="layout-logo">
        <div class="logo-symbol">Y</div>
        <strong v-if="!collapsed">Youni SEO</strong>
        <button
          class="icon-button"
          type="button"
          :aria-label="collapsed ? '展開側欄' : '收合側欄'"
          @click="$emit('toggle-sidebar')"
        >
          <AppIcon
            :name="collapsed ? 'chevron-right' : 'chevron-left'"
            :size="17"
          />
        </button>
      </div>

      <nav class="layout-navigation" aria-label="主要導覽">
        <template v-for="item in navigation" :key="item.id">
          <button
            class="navigation-item"
            :class="{ active: item.page === activePage, disabled: item.disabled }"
            type="button"
            :title="collapsed ? item.label : undefined"
            @click="
              item.page && !item.disabled
                ? $emit('navigate', item.page)
                : $emit('unavailable', item.label)
            "
          >
            <AppIcon :name="item.icon" :size="19" />
            <span v-if="!collapsed">{{ item.label }}</span>
            <small v-if="item.badge && !collapsed">{{ item.badge }}</small>
          </button>
        </template>
      </nav>

      <div class="layout-user">
        <span class="user-avatar">{{ user.displayName.slice(0, 1) }}</span>
        <div v-if="!collapsed" class="user-summary">
          <strong>{{ user.displayName }}</strong>
          <span>{{ user.email }}</span>
        </div>
        <button
          v-if="!collapsed"
          class="icon-button"
          type="button"
          aria-label="登出"
          @click="$emit('logout')"
        >
          <AppIcon name="logout" :size="17" />
        </button>
      </div>
    </aside>

    <header class="layout-topbar">
      <label class="global-search">
        <AppIcon name="search" :size="17" />
        <input
          :value="search"
          type="search"
          placeholder="搜尋客戶、任務、關鍵字..."
          @input="
            $emit(
              'update:search',
              ($event.target as HTMLInputElement).value,
            )
          "
        />
      </label>
      <div class="topbar-actions">
        <button
          class="icon-button"
          type="button"
          aria-label="重新整理"
          @click="$emit('refresh')"
        >
          <AppIcon name="refresh" :size="18" />
        </button>
        <button
          class="icon-button notification-button"
          type="button"
          aria-label="通知"
          @click="$emit('unavailable', '通知中心')"
        >
          <AppIcon name="bell" :size="18" />
          <span>2</span>
        </button>
      </div>
    </header>

    <main class="layout-content">
      <slot />
    </main>
  </div>
</template>
