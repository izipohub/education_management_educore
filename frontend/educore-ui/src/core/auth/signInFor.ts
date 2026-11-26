/**
 * Signing in for another application (Moodle's single sign-on, educore.learning.moodle_sso). EduCore's sign-in
 * server sends someone who is not signed in to "/login?redirect-to=<its authorisation address>"; once they are, the
 * browser goes back there, and EduCore sends them on to the application.
 *
 * Only EduCore's own authorisation address, on this origin, is followed: anything else would let a link send people
 * signing in to another site.
 */
export const AUTHORIZE_PATH = "/api/method/frappe.integrations.oauth2.authorize";

export function signInFor(value: unknown, origin: string): string | null {
  if (typeof value !== "string" || !value) return null;
  let url: URL;
  try {
    url = new URL(value, origin);
  } catch {
    return null;
  }
  return url.origin === origin && url.pathname === AUTHORIZE_PATH ? url.href : null;
}
