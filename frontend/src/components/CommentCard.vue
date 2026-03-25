<script setup>
import { computed, ref } from "vue";

import CommentComposer from "./CommentComposer.vue";

defineOptions({
  name: "CommentCard",
});

const props = defineProps({
  comment: {
    type: Object,
    required: true,
  },
  deleteAction: {
    type: Function,
    required: true,
  },
  guestProfile: {
    type: Object,
    default: () => ({
      username: "",
      email: "",
    }),
  },
  guestProfileChangeAction: {
    type: Function,
    required: true,
  },
  replyAction: {
    type: Function,
    required: true,
  },
  session: {
    type: Object,
    default: null,
  },
  updateAction: {
    type: Function,
    required: true,
  },
});

const editing = ref(false);
const replying = ref(false);

const isOwner = computed(() => props.session?.user?.id === props.comment.user);

function formatDate(timestamp) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

function isImage(attachment) {
  return /\.(gif|jpe?g|png)$/i.test(attachment.name || attachment.url);
}

async function handleDelete() {
  const confirmed = window.confirm("Soft-delete this comment?");
  if (!confirmed) {
    return;
  }

  await props.deleteAction(props.comment.id);
}

async function submitReply(payload) {
  const result = await props.replyAction(props.comment.id, payload);
  replying.value = false;
  return result;
}

async function submitUpdate(payload) {
  const result = await props.updateAction(props.comment.id, payload);
  editing.value = false;
  return result;
}
</script>

<template>
  <article class="comment-card" :class="{ deleted: comment.is_deleted }">
    <header class="comment-header">
      <div>
        <p class="comment-author">{{ comment.username }}</p>
        <p class="comment-meta">
          <span>{{ formatDate(comment.created_at) }}</span>
          <span v-if="comment.is_edited">edited</span>
          <span v-if="comment.replies_count">{{ comment.replies_count }} replies</span>
        </p>
      </div>

      <div class="comment-actions-inline">
        <button
          v-if="!comment.is_deleted"
          class="button ghost"
          type="button"
          @click="replying = !replying"
        >
          {{ replying ? "Close reply" : "Reply" }}
        </button>
        <button
          v-if="isOwner && !comment.is_deleted"
          class="button ghost"
          type="button"
          @click="editing = !editing"
        >
          {{ editing ? "Close edit" : "Edit" }}
        </button>
        <button
          v-if="isOwner && !comment.is_deleted"
          class="button danger"
          type="button"
          @click="handleDelete"
        >
          Delete
        </button>
      </div>
    </header>

    <div class="comment-body" v-html="comment.text" />

    <div v-if="comment.attachments.length" class="attachment-grid">
      <a
        v-for="attachment in comment.attachments"
        :key="attachment.id"
        :href="attachment.url"
        class="attachment-card"
        rel="noreferrer"
        target="_blank"
      >
        <img
          v-if="isImage(attachment)"
          :alt="attachment.name"
          :src="attachment.url"
          class="attachment-image"
        />
        <div class="attachment-meta">
          <strong>{{ attachment.name }}</strong>
          <span>{{ isImage(attachment) ? "Image preview" : "Text attachment" }}</span>
        </div>
      </a>
    </div>

    <CommentComposer
      v-if="replying"
      :guest-profile="guestProfile"
      :session="session"
      :show-cancel="true"
      :submit-action="submitReply"
      mode="reply"
      submit-label="Post reply"
      @cancel="replying = false"
      @guest-profile-change="guestProfileChangeAction"
    />

    <CommentComposer
      v-if="editing"
      :existing-attachments="comment.attachments"
      :guest-profile="guestProfile"
      :initial-text="comment.text"
      :session="session"
      :show-cancel="true"
      :submit-action="submitUpdate"
      mode="edit"
      submit-label="Save changes"
      @cancel="editing = false"
    />

    <section v-if="comment.children.length" class="reply-thread">
      <CommentCard
        v-for="reply in comment.children"
        :key="reply.id"
        :comment="reply"
        :delete-action="deleteAction"
        :guest-profile="guestProfile"
        :guest-profile-change-action="guestProfileChangeAction"
        :reply-action="replyAction"
        :session="session"
        :update-action="updateAction"
      />
    </section>
  </article>
</template>
