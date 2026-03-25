<script setup>
import { ref } from "vue";

const props = defineProps({
  loginAction: {
    type: Function,
    required: true,
  },
  registerAction: {
    type: Function,
    required: true,
  },
  session: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["logout"]);

const mode = ref("login");
const username = ref("");
const email = ref("");
const password = ref("");
const passwordConfirm = ref("");
const busy = ref(false);
const errorMessage = ref("");

function setMode(nextMode) {
  mode.value = nextMode;
  errorMessage.value = "";
  password.value = "";
  passwordConfirm.value = "";
}

async function handleSubmit() {
  busy.value = true;
  errorMessage.value = "";

  try {
    if (mode.value === "register") {
      await props.registerAction({
        username: username.value,
        email: email.value,
        password: password.value,
        password_confirm: passwordConfirm.value,
      });
    } else {
      await props.loginAction({
        username: username.value,
        password: password.value,
      });
    }

    password.value = "";
    passwordConfirm.value = "";
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="panel auth-panel">
    <div class="panel-heading">
      <p class="eyebrow">Identity</p>
      <h2>{{ session ? "Signed in" : mode === "register" ? "Create account" : "Author login" }}</h2>
    </div>

    <div v-if="session" class="auth-session">
      <p class="auth-user">{{ session.user.username }}</p>
      <p class="subtle">
        Edit and soft-delete are available for comments created by this account.
      </p>
      <button class="button secondary" @click="emit('logout')">Sign out</button>
    </div>

    <form v-else class="stack-sm" @submit.prevent="handleSubmit">
      <div class="sort-grid">
        <button
          class="sort-pill"
          :class="{ active: mode === 'login' }"
          type="button"
          @click="setMode('login')"
        >
          Sign in
        </button>
        <button
          class="sort-pill"
          :class="{ active: mode === 'register' }"
          type="button"
          @click="setMode('register')"
        >
          Register
        </button>
      </div>

      <label class="field">
        <span>Username</span>
        <input v-model="username" type="text" autocomplete="username" />
      </label>

      <label v-if="mode === 'register'" class="field">
        <span>Email</span>
        <input v-model="email" type="email" autocomplete="email" />
      </label>

      <label class="field">
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
        />
      </label>

      <label v-if="mode === 'register'" class="field">
        <span>Repeat password</span>
        <input
          v-model="passwordConfirm"
          type="password"
          autocomplete="new-password"
        />
      </label>

      <button class="button" type="submit" :disabled="busy">
        {{
          busy
            ? mode === "register"
              ? "Creating account..."
              : "Signing in..."
            : mode === "register"
              ? "Create account"
              : "Sign in"
        }}
      </button>

      <p class="subtle">
        {{
          mode === "register"
            ? "Create a local account with username, email, and password."
            : "Use an existing backend user, or the bootstrap superuser defined in the root .env."
        }}
      </p>

      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
    </form>
  </section>
</template>
