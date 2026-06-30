<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";
import type {
  NavigationItem,
  PageId,
  SessionUser,
} from "../types";
import { getFocusTargetIndex } from "../utils/focus-trap";

type CommandFocusElement = HTMLInputElement | HTMLButtonElement;

const props = defineProps<{
  user: SessionUser;
  activePage: PageId;
  currentTitle: string;
  navigation: NavigationItem[];
  collapsed: boolean;
  search: string;
}>();

const emit = defineEmits<{
  navigate: [page: PageId];
  logout: [];
  refresh: [];
  "toggle-sidebar": [];
  "update:search": [value: string];
  unavailable: [label: string];
}>();

const showSearch = ref(false);
const showUserMenu = ref(false);
const searchButton = ref<HTMLButtonElement | null>(null);
const commandInput = ref<HTMLInputElement | null>(null);
const commandEscapeButton = ref<HTMLButtonElement | null>(null);
const commandQuickActions = ref<HTMLButtonElement[]>([]);
const commandNavigationButtons = ref<HTMLButtonElement[]>([]);
const expandedNavigationIds = ref<Set<string>>(
  new Set(["geo-analysis", "permissions"]),
);

const primaryNavigation = computed(() =>
  props.navigation.filter((item) => !item.group),
);
const navigationGroups = computed(() => {
  const groups = new Map<string, NavigationItem[]>();
  for (const item of props.navigation) {
    if (!item.group) continue;
    groups.set(item.group, [...(groups.get(item.group) ?? []), item]);
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items }));
});
const commandNavigationItems = computed(() =>
  props.navigation.flatMap((item) => [
    ...(item.page ? [item] : []),
    ...(item.children?.filter((child) => child.page) ?? []),
  ]),
);
const breadcrumbSegments = computed(() => {
  if (props.activePage.startsWith("permissions-")) {
    return ["系統", "權限管理", props.currentTitle];
  }
  if (props.activePage.startsWith("geo-analysis-")) {
    return ["分析工具", "GEO 分析", props.currentTitle];
  }
  return [props.currentTitle];
});

function selectNavigation(item: NavigationItem): void {
  closeSearch(false);
  if (item.children?.length) {
    toggleNavigationGroup(item);
    return;
  }
  if (item.page && !item.disabled) {
    emit("navigate", item.page);
    return;
  }
  emit("unavailable", item.label);
}

function isNavigationActive(item: NavigationItem): boolean {
  return (
    item.page === props.activePage ||
    Boolean(item.children?.some((child) => child.page === props.activePage))
  );
}

function isNavigationExpanded(item: NavigationItem): boolean {
  return (
    expandedNavigationIds.value.has(item.id) ||
    Boolean(item.children?.some((child) => child.page === props.activePage))
  );
}

function toggleNavigationGroup(item: NavigationItem): void {
  if (props.collapsed) {
    const firstChild = item.children?.find((child) => child.page && !child.disabled);
    if (firstChild?.page) emit("navigate", firstChild.page);
    return;
  }
  const next = new Set(expandedNavigationIds.value);
  if (next.has(item.id)) next.delete(item.id);
  else next.add(item.id);
  expandedNavigationIds.value = next;
}

function openSearch(): void {
  showUserMenu.value = false;
  showSearch.value = true;
}

function closeSearch(restoreFocus = true): void {
  showSearch.value = false;
  if (restoreFocus) {
    void nextTick(() => searchButton.value?.focus());
  }
}

function handleSearchKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    closeSearch();
    return;
  }
  if (event.key !== "Tab") return;

  const focusableItems = [
    commandInput.value,
    commandEscapeButton.value,
    ...commandQuickActions.value,
    ...commandNavigationButtons.value,
  ].filter((item): item is CommandFocusElement => Boolean(item));
  if (!focusableItems.length) return;

  const currentIndex = focusableItems.indexOf(
    event.target as CommandFocusElement,
  );
  const targetIndex = getFocusTargetIndex(
    currentIndex,
    focusableItems.length,
    event.shiftKey,
  );
  const isLeavingDialog =
    currentIndex < 0 ||
    (!event.shiftKey && currentIndex === focusableItems.length - 1) ||
    (event.shiftKey && currentIndex === 0);
  if (!isLeavingDialog) return;

  event.preventDefault();
  focusableItems[targetIndex]?.focus();
}

function toggleUserMenu(): void {
  showSearch.value = false;
  showUserMenu.value = !showUserMenu.value;
}

function closeUserMenu(): void {
  showUserMenu.value = false;
}

function selectUserAction(label: string): void {
  closeUserMenu();
  emit("unavailable", label);
}

function logout(): void {
  closeUserMenu();
  emit("logout");
}
</script>

<template>
  <div class="layout" :class="{ 'layout-collapsed': collapsed }">
    <aside class="layout-sidebar">
      <div class="layout-logo">
        <strong v-if="!collapsed" class="layout-wordmark">Younilab SEO</strong>
        <span v-else class="logo-mark">Y</span>
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
        <template v-for="item in primaryNavigation" :key="item.id">
          <button
            class="navigation-item"
            :class="{ active: isNavigationActive(item), disabled: item.disabled }"
            type="button"
            :title="collapsed ? item.label : undefined"
            @click="selectNavigation(item)"
          >
            <AppIcon :name="item.icon" :size="19" />
            <span v-if="!collapsed">{{ item.label }}</span>
            <small v-if="item.badge && !collapsed">{{ item.badge }}</small>
          </button>
        </template>
        <section
          v-for="group in navigationGroups"
          :key="group.label"
          class="navigation-group"
        >
          <p v-if="!collapsed">{{ group.label }}</p>
          <template v-for="item in group.items" :key="item.id">
            <button
              class="navigation-item"
              :class="{
                active: isNavigationActive(item),
                disabled: item.disabled,
                'has-children': item.children?.length,
              }"
              type="button"
              :title="collapsed ? item.label : undefined"
              @click="selectNavigation(item)"
            >
              <AppIcon :name="item.icon" :size="17" />
              <span v-if="!collapsed">{{ item.label }}</span>
              <small v-if="item.badge && !collapsed">{{ item.badge }}</small>
              <AppIcon
                v-if="item.children?.length && !collapsed"
                class="navigation-expand-icon"
                :class="{ expanded: isNavigationExpanded(item) }"
                name="chevron-right"
                :size="13"
              />
            </button>
            <div
              v-if="item.children?.length && !collapsed && isNavigationExpanded(item)"
              class="navigation-submenu"
            >
              <button
                v-for="child in item.children"
                :key="child.id"
                class="navigation-subitem"
                :class="{ active: child.page === activePage, disabled: child.disabled }"
                type="button"
                @click="selectNavigation(child)"
              >
                <span>{{ child.label }}</span>
                <small v-if="child.badge">{{ child.badge }}</small>
              </button>
            </div>
          </template>
        </section>
      </nav>
    </aside>

    <header class="layout-topbar">
      <div class="topbar-breadcrumbs">
        <template
          v-for="(segment, index) in breadcrumbSegments"
          :key="`${segment}-${index}`"
        >
          <strong v-if="index === breadcrumbSegments.length - 1">
            {{ segment }}
          </strong>
          <span v-else>{{ segment }}</span>
          <AppIcon
            v-if="index < breadcrumbSegments.length - 1"
            name="chevron-right"
            :size="13"
          />
        </template>
      </div>
      <div class="topbar-actions">
        <button
          ref="searchButton"
          class="icon-button"
          type="button"
          aria-label="搜尋"
          @click="openSearch"
        >
          <AppIcon name="search" :size="18" />
        </button>
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
        <span class="topbar-divider"></span>
        <div class="topbar-user-wrap">
          <button
            class="topbar-user"
            type="button"
            :aria-expanded="showUserMenu"
            aria-haspopup="menu"
            @click="toggleUserMenu"
          >
            <span class="user-avatar">{{ user.displayName.slice(0, 1) }}</span>
            <AppIcon name="chevron-right" :size="13" />
          </button>
          <button
            v-if="showUserMenu"
            class="user-menu-backdrop"
            type="button"
            aria-label="關閉使用者選單"
            @click="closeUserMenu"
          ></button>
          <div v-if="showUserMenu" class="user-menu" role="menu">
            <div class="user-menu-head">
              <strong>{{ user.displayName }}</strong>
              <span>{{ user.email }}</span>
            </div>
            <button type="button" role="menuitem" @click="selectUserAction('個人資料')">
              <AppIcon name="user" :size="16" />個人資料
            </button>
            <button type="button" role="menuitem" @click="selectUserAction('帳號設定')">
              <AppIcon name="settings" :size="16" />帳號設定
            </button>
            <button class="danger" type="button" role="menuitem" @click="logout">
              <AppIcon name="logout" :size="16" />登出
            </button>
          </div>
        </div>
      </div>
    </header>

    <main class="layout-content">
      <slot />
    </main>

    <div
      v-if="showSearch"
      class="command-overlay"
      @click.self="closeSearch()"
      @keydown="handleSearchKeydown"
    >
      <section
        class="command-panel"
        role="dialog"
        aria-modal="true"
        aria-label="搜尋"
      >
        <label class="command-input">
          <AppIcon name="search" :size="18" />
          <input
            ref="commandInput"
            :value="search"
            type="search"
            autofocus
            placeholder="搜尋客戶、任務、關鍵字..."
            @input="
              $emit(
                'update:search',
                ($event.target as HTMLInputElement).value,
              )
            "
          />
          <button ref="commandEscapeButton" type="button" @click="closeSearch()">
            ESC
          </button>
        </label>
        <div class="command-list">
          <p>快速操作</p>
          <button
            ref="commandQuickActions"
            type="button"
            @click="$emit('unavailable', '新增客戶')"
          >
            <AppIcon name="plus" :size="16" />新增客戶
          </button>
          <button
            ref="commandQuickActions"
            type="button"
            @click="$emit('unavailable', '新增任務')"
          >
            <AppIcon name="plus" :size="16" />新增任務
          </button>
          <p>前往</p>
          <button
            v-for="item in commandNavigationItems"
            ref="commandNavigationButtons"
            :key="item.id"
            type="button"
            @click="selectNavigation(item)"
          >
            <AppIcon :name="item.icon" :size="16" />{{ item.label }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
