/* Same-origin API: the HttpOnly session cookie never enters JavaScript. */
class APIError extends Error {
  constructor(code) { super(code); this.code = code; }
}

const base = "/recommander/api/";
let csrf;
let initialization;

async function request(route, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(base + route, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
      headers: body === undefined ? {} : { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new APIError(data.error || "error");
    return data;
  } catch (error) {
    throw error instanceof APIError ? error : new APIError("error");
  } finally { clearTimeout(timeout); }
}

async function initialize() {
  if (!initialization) {
    initialization = request("session").then(data => { csrf = data.csrf; }).catch(error => {
      initialization = null;
      throw error;
    });
  }
  await initialization;
}

export const api = {
  get: route => request(route),
  async post(route, body) { await initialize(); return request(route, body); }
};
