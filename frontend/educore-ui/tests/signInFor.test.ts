import { describe, expect, it } from "vitest";
import { signInFor } from "@/core/auth/signInFor";

const ORIGIN = "https://app.educore.example";
const AUTHORIZE = `${ORIGIN}/api/method/frappe.integrations.oauth2.authorize?client_id=abc&response_type=code&redirect_uri=https%3A%2F%2Fmoodle.example%2Fadmin%2Foauth2callback.php`;

describe("signing in for Moodle", () => {
  it("goes back to EduCore's own authorisation address", () => {
    expect(signInFor(AUTHORIZE, ORIGIN)).toBe(AUTHORIZE);
    expect(signInFor("/api/method/frappe.integrations.oauth2.authorize?client_id=abc", ORIGIN)).toBe(
      `${ORIGIN}/api/method/frappe.integrations.oauth2.authorize?client_id=abc`,
    );
  });

  it("follows nothing else", () => {
    expect(signInFor("https://evil.example/api/method/frappe.integrations.oauth2.authorize", ORIGIN)).toBeNull();
    expect(signInFor("//evil.example/api/method/frappe.integrations.oauth2.authorize", ORIGIN)).toBeNull();
    expect(signInFor(`${ORIGIN}/api/method/frappe.auth.get_logged_user`, ORIGIN)).toBeNull();
    expect(signInFor("javascript:alert(1)", ORIGIN)).toBeNull();
    expect(signInFor(undefined, ORIGIN)).toBeNull();
    expect(signInFor(["/x"], ORIGIN)).toBeNull();
  });
});
