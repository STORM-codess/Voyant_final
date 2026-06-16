// Voyant — API helper. Central place for the backend base URL and for
// attaching the Firebase auth token to every request.
//
// Local backend runs at http://localhost:8000. When you deploy, change
// API_BASE (ideally via an env var like import.meta.env.VITE_API_BASE).

import { auth } from "./firebase";

export const API_BASE = "http://localhost:8000";

// Core fetch wrapper: attaches the current user's Firebase ID token as
// a Bearer header, parses JSON, throws on non-OK responses.
async function request(path, { method = "GET", body, auth: needsAuth = true } = {}) {
  const headers = { "Content-Type": "application/json" };

  if (needsAuth) {
    const user = auth.currentUser;
    if (!user) throw new Error("Not signed in");
    const token = await user.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // surface 404 etc. to the caller without throwing first, so callers
  // like "register if missing" can branch on status.
  if (!res.ok) {
    const err = new Error(`API ${res.status} on ${path}`);
    err.status = res.status;
    try { err.data = await res.json(); } catch { /* no json body */ }
    throw err;
  }
  // some endpoints may return empty bodies
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: "GET" }),
  post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
  patch: (path, body, opts) => request(path, { ...opts, method: "PATCH", body }),
  del: (path, opts) => request(path, { ...opts, method: "DELETE" }),
};

// ── Auth-specific calls (your real endpoints) ──

// Returns the current user's profile, or null if not yet registered.
export async function fetchMe() {
  try {
    return await api.get("/users/me");
  } catch (e) {
    if (e.status === 404) return null; // user exists in Firebase but not yet in our DB
    throw e;
  }
}

// Creates the user row in our DB. Backend wants { name, email }.
export async function registerUser({ name, email }) {
  return api.post("/users/register", { name, email });
}
