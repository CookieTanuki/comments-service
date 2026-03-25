const API_ORIGIN = (import.meta.env.VITE_API_ORIGIN || "").replace(/\/$/, "");
const WS_ORIGIN = (import.meta.env.VITE_WS_ORIGIN || "").replace(/\/$/, "");

function isAbsoluteUrl(value) {
  return /^https?:\/\//i.test(value);
}

function buildApiUrl(pathOrUrl) {
  if (isAbsoluteUrl(pathOrUrl)) {
    return pathOrUrl;
  }

  return `${API_ORIGIN}${pathOrUrl}`;
}

function buildSocketUrl() {
  if (WS_ORIGIN) {
    return `${WS_ORIGIN}/ws/comments/`;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/comments/`;
}

function createApiError(payload, status) {
  let message = "Request failed";

  if (typeof payload === "string" && payload.trim()) {
    message = payload;
  } else if (payload && typeof payload === "object") {
    if (payload.detail) {
      message = payload.detail;
    } else {
      const [field, value] = Object.entries(payload)[0] || [];
      if (field) {
        const firstValue = Array.isArray(value) ? value[0] : value;
        message = `${field}: ${firstValue}`;
      }
    }
  }

  const error = new Error(message);
  error.status = status;
  error.payload = payload;
  return error;
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw createApiError(payload, response.status);
  }

  return payload;
}

async function request(pathOrUrl, options = {}) {
  const { token, body, isForm = false, method = "GET" } = options;
  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (!isForm && body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildApiUrl(pathOrUrl), {
    method,
    headers,
    body: isForm || body === undefined ? body : JSON.stringify(body),
  });

  return parseResponse(response);
}

function buildCommentFormData(payload) {
  const formData = new FormData();

  formData.append("text", payload.text || "");

  if (payload.username) {
    formData.append("username", payload.username);
  }

  if (payload.email) {
    formData.append("email", payload.email);
  }

  if (payload.captchaKey) {
    formData.append("captcha_key", payload.captchaKey);
  }

  if (payload.captchaResponse) {
    formData.append("captcha_response", payload.captchaResponse);
  }

  for (const file of payload.files || []) {
    formData.append("uploaded_files", file);
  }

  for (const attachmentId of payload.removeAttachmentIds || []) {
    formData.append("remove_attachments", String(attachmentId));
  }

  return formData;
}

export function fetchComments({ ordering = "-created_at", url = null } = {}) {
  if (url) {
    return request(url);
  }

  const params = new URLSearchParams({ ordering });
  return request(`/comments/?${params.toString()}`);
}

export function previewComment(text) {
  return request("/comments/preview/", {
    method: "POST",
    body: { text },
  });
}

export function fetchCaptchaChallenge() {
  return request("/comments/captcha/");
}

export function login(credentials) {
  return request("/api/token/", {
    method: "POST",
    body: credentials,
  });
}

export function register(payload) {
  return request("/api/register/", {
    method: "POST",
    body: payload,
  });
}

export function createComment(payload, token) {
  return request("/comments/", {
    method: "POST",
    token,
    body: buildCommentFormData(payload),
    isForm: true,
  });
}

export function createReply(commentId, payload, token) {
  return request(`/comments/${commentId}/reply/`, {
    method: "POST",
    token,
    body: buildCommentFormData(payload),
    isForm: true,
  });
}

export function updateComment(commentId, payload, token) {
  return request(`/comments/${commentId}/`, {
    method: "PATCH",
    token,
    body: buildCommentFormData(payload),
    isForm: true,
  });
}

export function deleteComment(commentId, token) {
  return request(`/comments/${commentId}/delete/`, {
    method: "DELETE",
    token,
  });
}

export function connectCommentsSocket({ onEvent, onStatusChange }) {
  const socket = new WebSocket(buildSocketUrl());

  socket.addEventListener("open", () => {
    onStatusChange?.("live");
  });

  socket.addEventListener("close", () => {
    onStatusChange?.("offline");
  });

  socket.addEventListener("error", () => {
    onStatusChange?.("offline");
  });

  socket.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data);
      onEvent?.(payload);
    } catch (error) {
      console.error("Failed to parse websocket payload", error);
    }
  });

  return socket;
}
