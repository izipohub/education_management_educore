"""Moodle single sign-on: people sign in to Moodle with their EduCore login.

EduCore is the sign-in provider (Frappe's OAuth 2 / OpenID Connect server) and Moodle a trusted client of it: when
ICT chooses single sign-on on the Integrations screen, EduCore registers Moodle as an OAuth Client (no "allow
access?" screen: it is the university's own Moodle). Moodle's login page then offers "EduCore"; someone already
signed in to EduCore goes straight through, anyone else signs in on EduCore's own login page first.

Moodle matches the person to the account the class sync made (educore.learning.moodle) by email, and from then on by
EduCore's stable subject identifier. Moodle's side is set up with docs/integrations/moodle-setup.php and the values
from details(); see docs/integrations/moodle.md.

The addresses are the Vue app's (site config educore_app_url): its login page is where people sign in, and it
forwards /api to Frappe.
"""

import frappe

CLIENT = "Moodle"
#: what Moodle asks for when signing someone in; the client allows these
SCOPES = "openid profile email all"
AUTHORIZE = "/api/method/frappe.integrations.oauth2.authorize"
TOKEN = "/api/method/frappe.integrations.oauth2.get_token"
USERINFO = "/api/method/frappe.integrations.oauth2.openid_profile"


def _app_url() -> str:
	return (frappe.conf.get("educore_app_url") or frappe.utils.get_url()).rstrip("/")


def _callback(moodle_url: str) -> str:
	return f"{moodle_url.rstrip('/')}/admin/oauth2callback.php"


def client_name() -> str | None:
	return frappe.db.get_value("OAuth Client", {"app_name": CLIENT})


def ensure_client(moodle_url: str) -> str:
	"""Moodle as a trusted OAuth client of EduCore, sending people back to Moodle's address"""
	callback = _callback(moodle_url)
	name = client_name()
	doc = frappe.get_doc("OAuth Client", name) if name else frappe.new_doc("OAuth Client")
	doc.update(
		{
			"app_name": CLIENT,
			"scopes": SCOPES,
			"redirect_uris": callback,
			"default_redirect_uri": callback,
			"skip_authorization": 1,
			"grant_type": "Authorization Code",
			"response_type": "Code",
		}
	)
	if doc.meta.has_field("token_endpoint_auth_method"):
		doc.token_endpoint_auth_method = "Client Secret Post"
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	return doc.name


def remove_client():
	"""Single sign-on switched off: Moodle may no longer sign people in with EduCore"""
	name = client_name()
	if name:
		for token in frappe.get_all("OAuth Bearer Token", filters={"client": name, "status": "Active"}, pluck="name"):
			frappe.db.set_value("OAuth Bearer Token", token, "status", "Revoked")
		frappe.delete_doc("OAuth Client", name, ignore_permissions=True, force=True)


def details() -> dict | None:
	"""What ICT gives Moodle (the setup script's --sso flags): EduCore's address, the client and its secret"""
	name = client_name()
	if not name:
		return None
	client = frappe.db.get_value("OAuth Client", name, ["client_id", "client_secret", "default_redirect_uri"], as_dict=True)
	base = _app_url()
	return {
		"base_url": base,
		"client_id": client.client_id,
		"client_secret": client.client_secret,
		"redirect_uri": client.default_redirect_uri,
		"authorization_endpoint": base + AUTHORIZE,
		"token_endpoint": base + TOKEN,
		"userinfo_endpoint": base + USERINFO,
		"scopes": "openid profile email",
	}
