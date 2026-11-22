"""Who uses Frappe's Desk, and what they see there (AGENT.md 3.1).

EduCore has two interfaces: the Vue app for students, academics, officers and self-service; the Desk for
specialist back-office work (finance, payroll and HR administration, procurement, stores) and technical
administration.

- Only users with the Desk Access role (positions in roles.py) or System Manager can open the Desk. Anyone
  else who reaches /desk (for example straight after Frappe's own login page) is sent to the Vue app.
  Frappe's API stays open to every signed-in user: the Vue app is built on it.
- Desk users get the EduCore Back Office Module Profile, which hides the modules a university does not use.
  ICT Administrators (System Manager) see everything.

The Vue app's address is the site config value educore_app_url (default "/", for a production reverse
proxy that serves the Vue app at the site's root).
"""

import frappe

DESK_ROLES = ("Desk Access", "System Manager")
BACK_OFFICE_PROFILE = "EduCore Back Office"
#: modules a university back office has no use for; Selling stays (student Customers live there)
HIDDEN_MODULES = (
	"CRM",
	"Manufacturing",
	"Subcontracting",
	"Quality Management",
	"Support",
	"Maintenance",
	"Telephony",
	"EDI",
	"Build",
	"Studio",
	"Website",
)


def has_desk_access(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & set(DESK_ROLES))


def app_url() -> str:
	return frappe.conf.get("educore_app_url") or "/"


def redirect_from_desk(context):
	"""update_website_context hook: the Desk page sends users without Desk Access to the Vue app"""
	path = (frappe.request.path if getattr(frappe, "request", None) else "") or ""
	if not (path == "/desk" or path.startswith("/desk/")):
		return
	user = frappe.session.user
	if user == "Guest" or has_desk_access(user):
		return  # guests get Frappe's own login redirect
	frappe.redirect(app_url())


def ensure_module_profile():
	"""The back-office Module Profile, kept as defined above"""
	if frappe.db.exists("Module Profile", BACK_OFFICE_PROFILE):
		profile = frappe.get_doc("Module Profile", BACK_OFFICE_PROFILE)
	else:
		profile = frappe.new_doc("Module Profile")
		profile.module_profile_name = BACK_OFFICE_PROFILE
	existing = set(frappe.get_all("Module Def", pluck="name"))
	wanted = [m for m in HIDDEN_MODULES if m in existing]
	if sorted(row.module for row in profile.block_modules) != sorted(wanted):
		profile.block_modules = []
		for module in wanted:
			profile.append("block_modules", {"module": module})
		profile.save(ignore_permissions=True)


def assign_module_profile(doc, method=None):
	"""User validate: a Desk user without a Module Profile gets the back-office one (not System Managers)"""
	if doc.name in ("Administrator", "Guest") or doc.module_profile:
		return
	roles = {row.role for row in doc.roles}
	if "Desk Access" in roles and "System Manager" not in roles and frappe.db.exists("Module Profile", BACK_OFFICE_PROFILE):
		doc.module_profile = BACK_OFFICE_PROFILE
		# User.validate copied the (then empty) profile's modules before this hook ran: copy them again
		doc.validate_allowed_modules()


def sync():
	ensure_module_profile()
	# existing desk users created before the profile existed (users who receive Desk Access later, through
	# a Role Profile update, get it from the User validate hook when that update saves them)
	desk_users = frappe.get_all("Has Role", filters={"role": "Desk Access", "parenttype": "User"}, pluck="parent")
	for user in set(desk_users):
		profile = frappe.db.get_value("User", user, "module_profile")
		blocked = frappe.db.count("Block Module", {"parent": user, "parenttype": "User"})
		if not profile or (profile == BACK_OFFICE_PROFILE and not blocked):
			frappe.get_doc("User", user).save(ignore_permissions=True)
