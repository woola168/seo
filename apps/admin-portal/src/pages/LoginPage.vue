<script setup lang="ts">
import { ref } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";

defineProps<{
  loading: boolean;
  error: string;
}>();

const emit = defineEmits<{
  login: [email: string, password: string];
  forgot: [];
  unavailable: [label: string];
}>();

const email = ref("");
const password = ref("");
const remember = ref(false);
const showPassword = ref(false);

function submit(): void {
  emit("login", email.value.trim(), password.value);
}
</script>

<template>
  <main class="login-page">
    <section class="login-visual">
      <div class="login-visual-pattern"></div>
      <div class="login-visual-brand">
        <strong>Youni SEO</strong>
        <span>智能內容管理，讓內容更有力量</span>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-form-wrap">
        <div class="login-brand">
          <span class="brand-cube"></span>
          <div>
            <strong>Youni SEO</strong>
            <span>文章管理系統</span>
          </div>
        </div>

        <div class="login-heading">
          <h1>歡迎回來</h1>
          <p>登入以繼續使用您的工作區</p>
        </div>

        <button
          class="button button-secondary google-button"
          type="button"
          @click="$emit('unavailable', 'Google 登入')"
        >
          <span class="google-mark">G</span>
          使用 Google 帳號登入
        </button>

        <div class="login-divider"><span>或使用帳號密碼</span></div>

        <form @submit.prevent="submit">
          <label class="form-field">
            <span>信箱</span>
            <span class="input-with-icon">
              <input
                v-model="email"
                type="email"
                autocomplete="username"
                placeholder="your@email.com"
                required
              />
              <AppIcon name="user" :size="16" />
            </span>
          </label>

          <label class="form-field">
            <span>密碼</span>
            <span class="input-with-icon">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="輸入密碼"
                required
              />
              <button
                class="input-action"
                type="button"
                :aria-label="showPassword ? '隱藏密碼' : '顯示密碼'"
                @click="showPassword = !showPassword"
              >
                <AppIcon :name="showPassword ? 'eye' : 'lock'" :size="16" />
              </button>
            </span>
          </label>

          <div class="login-options">
            <label class="checkbox-row">
              <input v-model="remember" type="checkbox" />
              <span>記住我</span>
            </label>
            <button
              class="text-button"
              type="button"
              @click="$emit('forgot')"
            >
              忘記密碼？
            </button>
          </div>

          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button
            class="button button-primary login-submit"
            type="submit"
            :disabled="loading"
          >
            {{ loading ? "登入中..." : "登入" }}
          </button>
        </form>

        <p class="login-signup">
          還沒有帳號？
          <button
            class="text-button"
            type="button"
            @click="$emit('unavailable', '申請試用')"
          >
            申請試用
          </button>
        </p>
        <p class="system-status"><span></span>系統狀態：正常 · v0.1.0</p>
      </div>
    </section>
  </main>
</template>
