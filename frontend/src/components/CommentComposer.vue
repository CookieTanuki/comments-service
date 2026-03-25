<script setup>
import { computed, onMounted, ref, watch } from "vue";

import { fetchCaptchaChallenge, previewComment } from "../lib/api";

const props = defineProps({
  existingAttachments: {
    type: Array,
    default: () => [],
  },
  guestProfile: {
    type: Object,
    default: () => ({
      username: "",
      email: "",
    }),
  },
  initialText: {
    type: String,
    default: "",
  },
  mode: {
    type: String,
    default: "create",
  },
  session: {
    type: Object,
    default: null,
  },
  showCancel: {
    type: Boolean,
    default: false,
  },
  submitAction: {
    type: Function,
    required: true,
  },
  submitLabel: {
    type: String,
    default: "Post comment",
  },
});

const emit = defineEmits(["cancel", "guest-profile-change", "saved"]);

const captcha = ref(null);
const captchaAnswer = ref("");
const fileInputKey = ref(0);
const files = ref([]);
const formError = ref("");
const loadingCaptcha = ref(false);
const loadingPreview = ref(false);
const previewHtml = ref("");
const removeAttachmentIds = ref([]);
const submitting = ref(false);
const text = ref(props.initialText);
const username = ref(props.guestProfile.username || "");
const email = ref(props.guestProfile.email || "");

const needsCaptcha = computed(() => !props.session?.access && props.mode !== "edit");
const includeGuestIdentity = computed(() => !props.session?.access && props.mode !== "edit");

watch(
  () => props.initialText,
  (value) => {
    text.value = value;
  },
);

watch(
  () => props.guestProfile,
  (value) => {
    if (props.mode !== "edit") {
      if (includeGuestIdentity.value) {
        username.value = value?.username || "";
        email.value = value?.email || "";
        return;
      }

      username.value = "";
      email.value = "";
    }
  },
  { deep: true },
);

async function loadCaptcha() {
  if (!needsCaptcha.value) {
    captcha.value = null;
    captchaAnswer.value = "";
    return;
  }

  loadingCaptcha.value = true;
  formError.value = "";

  try {
    captcha.value = await fetchCaptchaChallenge();
  } catch (error) {
    formError.value = error.message;
  } finally {
    loadingCaptcha.value = false;
  }
}

onMounted(() => {
  loadCaptcha();
});

watch(
  () => props.session?.access,
  () => {
    loadCaptcha();

    if (!includeGuestIdentity.value) {
      username.value = "";
      email.value = "";
      return;
    }

    username.value = props.guestProfile.username || "";
    email.value = props.guestProfile.email || "";
  },
);

function onFilesSelected(event) {
  files.value = Array.from(event.target.files || []);
}

function toggleAttachmentRemoval(attachmentId) {
  if (removeAttachmentIds.value.includes(attachmentId)) {
    removeAttachmentIds.value = removeAttachmentIds.value.filter((id) => id !== attachmentId);
    return;
  }

  removeAttachmentIds.value = [...removeAttachmentIds.value, attachmentId];
}

async function renderPreview() {
  loadingPreview.value = true;
  formError.value = "";

  try {
    const payload = await previewComment(text.value);
    previewHtml.value = payload.preview;
  } catch (error) {
    formError.value = error.message;
  } finally {
    loadingPreview.value = false;
  }
}

async function handleSubmit() {
  submitting.value = true;
  formError.value = "";

  try {
    const payload = {
      text: text.value,
      files: files.value,
      removeAttachmentIds: removeAttachmentIds.value,
      captchaKey: captcha.value?.key,
      captchaResponse: captchaAnswer.value,
    };

    if (includeGuestIdentity.value) {
      payload.username = username.value;
      payload.email = email.value;
    }

    const result = await props.submitAction(payload);

    emit("saved", result);

    if (!props.session?.access && props.mode !== "edit") {
      emit("guest-profile-change", {
        username: username.value,
        email: email.value,
      });
    }

    if (props.mode !== "edit") {
      text.value = "";
      files.value = [];
      captchaAnswer.value = "";
      previewHtml.value = "";
      fileInputKey.value += 1;
      await loadCaptcha();
    }
  } catch (error) {
    formError.value = error.message;
    if (needsCaptcha.value) {
      await loadCaptcha();
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <form class="composer panel" @submit.prevent="handleSubmit">
    <div class="panel-heading">
      <p class="eyebrow">{{ mode === "edit" ? "Redaction" : "Compose" }}</p>
      <h2>{{ submitLabel }}</h2>
    </div>

    <label class="field">
      <span>Comment</span>
      <textarea
        v-model="text"
        rows="5"
        placeholder="Write a thoughtful comment. Basic HTML is sanitized server-side."
      />
    </label>

    <div v-if="!session?.access && mode !== 'edit'" class="identity-grid">
      <label class="field">
        <span>Name</span>
        <input v-model="username" type="text" />
      </label>

      <label class="field">
        <span>Email</span>
        <input v-model="email" type="email" />
      </label>
    </div>

    <div v-if="existingAttachments.length" class="attachment-edit-list">
      <p class="subheading">Existing attachments</p>
      <label
        v-for="attachment in existingAttachments"
        :key="attachment.id"
        class="attachment-toggle"
      >
        <input
          :checked="removeAttachmentIds.includes(attachment.id)"
          type="checkbox"
          @change="toggleAttachmentRemoval(attachment.id)"
        />
        <span>{{ attachment.name }}</span>
      </label>
    </div>

    <label class="field">
      <span>Attachments</span>
      <input
        :key="fileInputKey"
        accept=".png,.jpg,.jpeg,.gif,.txt"
        multiple
        type="file"
        @change="onFilesSelected"
      />
    </label>

    <ul v-if="files.length" class="file-list">
      <li v-for="file in files" :key="file.name + file.size">{{ file.name }}</li>
    </ul>

    <div v-if="needsCaptcha" class="captcha-box">
      <div class="captcha-header">
        <p class="subheading">Captcha</p>
        <button class="button ghost" type="button" @click="loadCaptcha">
          {{ loadingCaptcha ? "Refreshing..." : "Refresh" }}
        </button>
      </div>

      <img
        v-if="captcha"
        :src="captcha.image_url"
        alt="Captcha challenge"
        class="captcha-image"
      />

      <label class="field">
        <span>Answer</span>
        <input v-model="captchaAnswer" type="text" />
      </label>
    </div>

    <div class="composer-actions">
      <button class="button secondary" type="button" @click="renderPreview">
        {{ loadingPreview ? "Rendering..." : "Preview" }}
      </button>
      <button v-if="showCancel" class="button ghost" type="button" @click="emit('cancel')">
        Cancel
      </button>
      <button class="button" type="submit" :disabled="submitting">
        {{ submitting ? "Saving..." : submitLabel }}
      </button>
    </div>

    <div v-if="previewHtml" class="preview-box">
      <p class="subheading">Preview</p>
      <div class="preview-html" v-html="previewHtml" />
    </div>

    <p v-if="formError" class="form-error">{{ formError }}</p>
  </form>
</template>
