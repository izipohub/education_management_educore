import axios, { AxiosError } from "axios";

/**
 * The one way the app talks to Frappe. Frappe's whitelisted methods live at /api/method/<dotted.path>
 * and answer {"message": …}; call() unwraps that. Errors become ApiError with the message Frappe meant
 * for the user, never a stack trace.
 */
export const http = axios.create({
  baseURL: "/",
  withCredentials: true,
  headers: { Accept: "application/json" },
});

let csrfToken: string | null = null;

/** Frappe checks this header on every POST/PUT/DELETE of a signed-in session (see educore.api.v1.session) */
export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

http.interceptors.request.use((config) => {
  if (csrfToken && config.method && config.method.toLowerCase() !== "get") {
    config.headers.set("X-Frappe-CSRF-Token", csrfToken);
  }
  return config;
});

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** Frappe's exception class, e.g. PermissionError, ValidationError, AuthenticationError */
    readonly type: string | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface FrappeErrorBody {
  exc_type?: string;
  exception?: string;
  message?: string;
  _server_messages?: string;
}

/** The human message in a Frappe error: _server_messages (a JSON list of JSON objects), else the exception */
export function frappeErrorMessage(body: FrappeErrorBody | undefined, fallback: string): string {
  if (body?._server_messages) {
    try {
      const messages = JSON.parse(body._server_messages) as string[];
      const first = JSON.parse(messages[0] ?? "{}") as { message?: string };
      if (first.message) return stripTags(first.message);
    } catch {
      // fall through to the next source
    }
  }
  if (typeof body?.message === "string") return stripTags(body.message);
  if (body?.exception) return stripTags(body.exception.replace(/^[\w.]+:\s*/, ""));
  return fallback;
}

function stripTags(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return (doc.body.textContent ?? "").trim();
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? 0;
    const body = error.response?.data as FrappeErrorBody | undefined;
    const fallback = status ? `Request failed (${status})` : "The server could not be reached";
    return new ApiError(frappeErrorMessage(body, fallback), status, body?.exc_type ?? null);
  }
  return new ApiError(String(error), 0, null);
}

/** GET a whitelisted method (reads) */
export async function get<T>(method: string, params?: Record<string, unknown>): Promise<T> {
  try {
    const response = await http.get<{ message: T }>(`/api/method/${method}`, { params });
    return response.data.message;
  } catch (error) {
    throw toApiError(error);
  }
}

/** POST to a whitelisted method (changes) */
export async function post<T>(method: string, data?: Record<string, unknown>): Promise<T> {
  try {
    const response = await http.post<{ message: T }>(`/api/method/${method}`, data ?? {});
    return response.data.message;
  } catch (error) {
    throw toApiError(error);
  }
}
