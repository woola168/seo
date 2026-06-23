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
      <div class="login-visual-brand">
        <strong>Younilab SEO</strong>
        <span>以數據驅動策略，建立搜尋上的長期優勢。</span>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-form-wrap">
        <div class="login-heading">
          <h1>歡迎回來</h1>
          <p>Younilab SEO 後台管理系統</p>
        </div>

        <button
          class="button button-secondary google-button"
          type="button"
          @click="$emit('unavailable', 'Google 登入')"
        >
          <svg class="google-mark" viewBox="0 0 18 18" aria-hidden="true">
            <path
              d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
              fill="#4285f4"
            />
            <path
              d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
              fill="#34a853"
            />
            <path
              d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
              fill="#fbbc05"
            />
            <path
              d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58Z"
              fill="#ea4335"
            />
          </svg>
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
              <AppIcon name="mail" :size="16" />
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
                <AppIcon name="eye" :size="16" />
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

        <!-- <p class="login-signup">
          還沒有帳號？
          <button
            class="text-button"
            type="button"
            @click="$emit('unavailable', '申請試用')"
          >
            申請試用
          </button>
        </p> -->
        <p class="system-status"><span></span>系統狀態：正常 · v2.2.0</p>
      </div>
    </section>
  </main>
</template>
