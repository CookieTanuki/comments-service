<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import AuthPanel from "./components/AuthPanel.vue";
import CommentCard from "./components/CommentCard.vue";
import CommentComposer from "./components/CommentComposer.vue";
import {
  connectCommentsSocket,
  createComment,
  createReply,
  deleteComment,
  fetchComments,
  login,
  register,
  updateComment,
} from "./lib/api";

const ORDER_OPTIONS = [
  { label: "Newest", value: "-created_at" },
  { label: "Oldest", value: "created_at" },
  { label: "A-Z", value: "username" },
  { label: "Email", value: "email" },
];

const SESSION_STORAGE_KEY = "threadline-session";
const GUEST_STORAGE_KEY = "threadline-guest";

function readStorage(key, fallback) {
  const raw = localStorage.getItem(key);

  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error(`Failed to parse ${key}`, error);
    return fallback;
  }
}

const session = ref(readStorage(SESSION_STORAGE_KEY, null));
const guestProfile = ref(
  readStorage(GUEST_STORAGE_KEY, {
    username: "",
    email: "",
  }),
);

const activeOrdering = ref("-created_at");
const currentPageUrl = ref(null);
const feed = ref({
  count: 0,
  next: null,
  previous: null,
  results: [],
});
const feedError = ref("");
const loadingFeed = ref(false);
const notice = ref("Live comments, nested replies, previews, uploads, and soft delete.");
const socketStatus = ref("connecting");

let socket = null;
let reconnectTimer = null;
let refreshTimer = null;

watch(session, (value) => {
  if (value) {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(value));
    return;
  }

  localStorage.removeItem(SESSION_STORAGE_KEY);
}, { deep: true });

watch(guestProfile, (value) => {
  localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(value));
}, { deep: true });

const statusLabel = computed(() => {
  if (socketStatus.value === "live") {
    return "Realtime connected";
  }

  if (socketStatus.value === "offline") {
    return "Realtime reconnecting";
  }

  return "Realtime starting";
});

async function loadFeed(url = null) {
  loadingFeed.value = true;
  feedError.value = "";

  try {
    feed.value = await fetchComments({
      ordering: activeOrdering.value,
      url,
    });
    currentPageUrl.value = url;
  } catch (error) {
    feedError.value = error.message;
  } finally {
    loadingFeed.value = false;
  }
}

function scheduleRefresh() {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  refreshTimer = setTimeout(() => {
    loadFeed(currentPageUrl.value);
  }, 150);
}

function connectSocket() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (socket) {
    socket.close();
  }

  socketStatus.value = "connecting";
  socket = connectCommentsSocket({
    onEvent(event) {
      notice.value = `Realtime update: ${event.type}`;
      scheduleRefresh();
    },
    onStatusChange(status) {
      socketStatus.value = status;
      if (status === "offline") {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connectSocket();
        }, 2000);
      }
    },
  });
}

function withSessionGuard(action) {
  return async (...args) => {
    try {
      return await action(...args);
    } catch (error) {
      if (error.status === 401) {
        session.value = null;
        notice.value = "Session expired. Sign in again to edit or delete comments.";
      }
      throw error;
    }
  };
}

const postComment = withSessionGuard(async (payload) => {
  const result = await createComment(payload, session.value?.access);
  notice.value = "Comment posted.";
  await loadFeed();
  return result;
});

const postReply = withSessionGuard(async (commentId, payload) => {
  const result = await createReply(commentId, payload, session.value?.access);
  notice.value = "Reply posted.";
  await loadFeed(currentPageUrl.value);
  return result;
});

const saveComment = withSessionGuard(async (commentId, payload) => {
  const result = await updateComment(commentId, payload, session.value?.access);
  notice.value = "Comment updated.";
  await loadFeed(currentPageUrl.value);
  return result;
});

const removeComment = withSessionGuard(async (commentId) => {
  await deleteComment(commentId, session.value?.access);
  notice.value = "Comment soft-deleted.";
  await loadFeed(currentPageUrl.value);
});

async function loginUser(credentials) {
  const auth = await login(credentials);
  session.value = auth;
  notice.value = `Signed in as ${auth.user.username}.`;
  await loadFeed(currentPageUrl.value);
}

async function registerUser(credentials) {
  await register(credentials);

  const auth = await login({
    username: credentials.username,
    password: credentials.password,
  });

  session.value = auth;
  notice.value = `Account created and signed in as ${auth.user.username}.`;
  await loadFeed(currentPageUrl.value);
}

function logoutUser() {
  session.value = null;
  notice.value = "Signed out. Anonymous posting still works with captcha.";
}

function updateGuestProfile(value) {
  guestProfile.value = value;
}

function changeOrdering(ordering) {
  activeOrdering.value = ordering;
  currentPageUrl.value = null;
  loadFeed();
}

onMounted(() => {
  loadFeed();
  connectSocket();
});

onBeforeUnmount(() => {
  if (socket) {
    socket.close();
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
  }

  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }
});
</script>

<template>
  <div class="app-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Threadline</p>
        <h1>Reddit-like discussion board with uploads, preview, live refresh, and soft delete.</h1>
      </div>
      <div class="status-chip" :class="socketStatus">{{ statusLabel }}</div>
    </header>

    <main class="layout">
      <aside class="sidebar stack-lg">
        <AuthPanel
          :login-action="loginUser"
          :register-action="registerUser"
          :session="session"
          @logout="logoutUser"
        />

        <section class="panel">
          <div class="panel-heading">
            <p class="eyebrow">Feed</p>
            <h2>Ordering</h2>
          </div>

          <div class="sort-grid">
            <button
              v-for="option in ORDER_OPTIONS"
              :key="option.value"
              :class="['sort-pill', { active: option.value === activeOrdering }]"
              @click="changeOrdering(option.value)"
            >
              {{ option.label }}
            </button>
          </div>

          <p class="subtle">{{ feed.count }} top-level comments currently indexed.</p>
        </section>

        <section class="panel">
          <div class="panel-heading">
            <p class="eyebrow">Status</p>
            <h2>Activity</h2>
          </div>
          <p class="notice">{{ notice }}</p>
          <p class="subtle">
            Anonymous posts require captcha. Authenticated posts inherit username and email
            from the signed-in account.
          </p>
        </section>
      </aside>

      <section class="content stack-lg">
        <CommentComposer
          :guest-profile="guestProfile"
          :session="session"
          :submit-action="postComment"
          mode="create"
          submit-label="Post top-level comment"
          @guest-profile-change="updateGuestProfile"
        />

        <section class="panel feed-panel">
          <div class="feed-toolbar">
            <div>
              <p class="eyebrow">Discussion</p>
              <h2>Recent threads</h2>
            </div>

            <div class="pagination-buttons">
              <button
                class="button ghost"
                :disabled="!feed.previous"
                @click="loadFeed(feed.previous)"
              >
                Previous
              </button>
              <button
                class="button ghost"
                :disabled="!feed.next"
                @click="loadFeed(feed.next)"
              >
                Next
              </button>
            </div>
          </div>

          <p v-if="loadingFeed" class="subtle">Loading comments…</p>
          <p v-else-if="feedError" class="form-error">{{ feedError }}</p>

          <div v-else class="comment-list">
            <CommentCard
              v-for="comment in feed.results"
              :key="comment.id"
              :comment="comment"
              :delete-action="removeComment"
              :guest-profile="guestProfile"
              :guest-profile-change-action="updateGuestProfile"
              :reply-action="postReply"
              :session="session"
              :update-action="saveComment"
            />
          </div>
        </section>
      </section>
    </main>
  </div>
</template>
