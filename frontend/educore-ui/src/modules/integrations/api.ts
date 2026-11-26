import { get, post } from "@/core/api/client";

export interface MoodleSettings {
  moodle_enabled: 0 | 1;
  moodle_url: string | null;
  sign_in: string;
  campus_categories: 0 | 1;
  student_role_id: number;
  teacher_role_id: number;
  has_token: boolean;
  last_sync_on: string | null;
  last_sync_result: string | null;
}

export interface Integrations {
  moodle: MoodleSettings;
  classes: { total: number; in_moodle: number; failed: { name: string; error: string }[] };
  sign_in_options: string[];
  /** with single sign-on: what ICT gives Moodle (the setup script's --sso flags; docs/integrations/moodle.md) */
  sso: {
    base_url: string;
    client_id: string;
    client_secret: string;
    redirect_uri: string;
    authorization_endpoint: string;
    token_endpoint: string;
    userinfo_endpoint: string;
    scopes: string;
  } | null;
}

/** ICT (educore.api.v1.integrations.ICT_ROLES) */
export const ICT_ROLES = ["System Manager"];

const API = "educore.api.v1.integrations";
export const getIntegrations = () => get<Integrations>(`${API}.settings`);
export const saveIntegrations = (data: Partial<MoodleSettings> & { moodle_token?: string }) => post<Integrations>(`${API}.save`, { data });
export const testMoodle = (url?: string, token?: string) =>
  post<{ ok: boolean; site?: string; release?: string; user?: string; error?: string; missing?: string[] }>(`${API}.test`, { url, token });
export const syncMoodleNow = () => post<{ queued: boolean }>(`${API}.sync_now`, {});
