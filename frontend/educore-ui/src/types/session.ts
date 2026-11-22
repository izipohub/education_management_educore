/** educore.api.v1.session.me */
export interface Me {
  user: string;
  full_name: string;
  first_name: string;
  user_image: string | null;
  /** Role Profiles: Registrar, Lecturer, … */
  positions: string[];
  roles: string[];
  /** Campuses the user is limited to; empty means the whole university */
  campuses: string[];
  /** Faculties / departments the user is limited to; empty means all */
  units: string[];
  /** The user's Student record, if they are a student */
  student: string | null;
  csrf_token: string;
}

/** educore_theme.branding.public_branding */
export interface Branding {
  institution_name: string;
  login_subtitle: string;
  logo: string;
  logo_on_dark: string;
  mark: string;
  favicon: string;
  primary_color: string;
  accent_color: string;
  background_color: string;
  text_on_accent: string;
  login_heading: string;
  login_heading_accent: string;
  login_text: string;
  facts: [string, string][];
  login_background: string;
}
