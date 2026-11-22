import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/core/api/client";
import type { Me } from "@/types/session";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), setCsrfToken: vi.fn() }));
vi.mock("@/core/api/client", async (original) => ({
  ...(await original<typeof import("@/core/api/client")>()),
  get: api.get,
  post: api.post,
  setCsrfToken: api.setCsrfToken,
}));

const { useSession } = await import("@/core/auth/session");

const officer: Me = {
  user: "registry-officer.osh@educore.localhost",
  full_name: "Registry Officer Oshakati",
  first_name: "Registry Officer",
  user_image: null,
  positions: ["Registry Officer"],
  roles: ["Registry Officer", "University Staff", "Academics User"],
  campuses: ["Oshakati Campus"],
  units: [],
  student: null,
  csrf_token: "token-123",
};

describe("session", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("loads the signed-in user and hands the CSRF token to the API client", async () => {
    api.get.mockResolvedValue(officer);
    const session = useSession();
    await session.load();
    expect(session.isSignedIn).toBe(true);
    expect(session.hasRole("Registry Officer")).toBe(true);
    expect(session.hasRole("Bursar")).toBe(false);
    expect(api.setCsrfToken).toHaveBeenCalledWith("token-123");
  });

  it("treats Frappe's 403 for a guest as signed out, not as an error", async () => {
    api.get.mockRejectedValue(new ApiError("Not permitted", 403, "PermissionError"));
    const session = useSession();
    await session.load();
    expect(session.isSignedIn).toBe(false);
    expect(session.loaded).toBe(true);
  });

  it("lets a real failure through", async () => {
    api.get.mockRejectedValue(new ApiError("Server error", 500, null));
    await expect(useSession().load()).rejects.toThrow("Server error");
  });

  it("retries a sign-in once when the server fails, not when the details are wrong", async () => {
    api.get.mockResolvedValue(officer);
    // Frappe can fail a login when the same user signs in twice at once: the second try goes through
    api.post.mockRejectedValueOnce(new ApiError("(1305, 'SAVEPOINT x does not exist')", 500, null)).mockResolvedValueOnce("Logged In");
    await useSession().login("registry-officer.osh@educore.localhost", "secret");
    expect(api.post).toHaveBeenCalledTimes(2);

    api.post.mockReset();
    api.post.mockRejectedValue(new ApiError("Incorrect password", 401, "AuthenticationError"));
    await expect(useSession().login("registry-officer.osh@educore.localhost", "wrong")).rejects.toThrow("Incorrect password");
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it("signs in through Frappe and then loads the user", async () => {
    api.post.mockResolvedValue("Logged In");
    api.get.mockResolvedValue(officer);
    const session = useSession();
    await session.login("registry-officer.osh@educore.localhost", "secret");
    expect(api.post).toHaveBeenCalledWith("login", { usr: "registry-officer.osh@educore.localhost", pwd: "secret" });
    expect(session.me?.campuses).toEqual(["Oshakati Campus"]);
  });

  it("forgets the user on sign out, even if the server call fails", async () => {
    api.get.mockResolvedValue(officer);
    api.post.mockRejectedValue(new ApiError("gone", 0, null));
    const session = useSession();
    await session.load();
    await expect(session.logout()).rejects.toThrow();
    expect(session.isSignedIn).toBe(false);
    expect(api.setCsrfToken).toHaveBeenLastCalledWith(null);
  });
});
