"""The signed-in user, for the Vue app: who they are, which positions they hold, where they work."""

import frappe
from frappe.sessions import get_csrf_token


@frappe.whitelist(methods=["GET"])
def me() -> dict:
	"""Guests get Frappe's 403; the app then shows its login page.

	csrf_token: Frappe checks it on every POST/PUT/DELETE of a signed-in session and hands it only to pages
	it renders itself. The Vue app is not one of those, so it reads the token here and sends it back as the
	X-Frappe-CSRF-Token header. Only the same origin can read this response.
	"""
	user = frappe.get_cached_doc("User", frappe.session.user)
	permissions = frappe.get_all(
		"User Permission",
		filters={"user": user.name, "allow": ("in", ("Campus", "Department"))},
		fields=["allow", "for_value"],
	)
	return {
		"user": user.name,
		"full_name": user.full_name,
		"first_name": user.first_name,
		"user_image": user.user_image,
		"positions": [row.role_profile for row in user.role_profiles],
		"roles": frappe.get_roles(user.name),
		# empty: the whole university
		"campuses": sorted(p.for_value for p in permissions if p.allow == "Campus"),
		"units": sorted(p.for_value for p in permissions if p.allow == "Department"),
		"student": frappe.db.get_value("Student", {"user": user.name}),
		"csrf_token": get_csrf_token(),
	}
