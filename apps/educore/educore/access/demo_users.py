"""One demo user per position, for trying each role on a development site.

    bench --site educore.localhost execute educore.access.demo_users.create

Users are <position>@educore.localhost (registrar@…, faculty-officer@…), named after their position,
with one shared password: EDUCORE_DEMO_PASSWORD from the environment, or DEFAULT_PASSWORD. Existing demo
users keep their password and get their position back if it was removed. Refuses to run on a site that is
not a *.localhost development site: real users are created by HR and the registry, not by this script.
"""

import os
import re

import frappe

from educore.access.roles import all_positions

DEFAULT_PASSWORD = "Campus-Demo-2026"
DOMAIN = "educore.localhost"


def email_for(position: str) -> str:
	return f"{re.sub(r'[^a-z0-9]+', '-', position.lower()).strip('-')}@{DOMAIN}"


def _assert_development_site():
	if not (frappe.local.site or "").endswith(".localhost"):
		frappe.throw(f"Demo users are only for a *.localhost development site, not {frappe.local.site}")


def create(password: str | None = None) -> list[str]:
	_assert_development_site()
	password = password or os.environ.get("EDUCORE_DEMO_PASSWORD") or DEFAULT_PASSWORD
	created = []
	# a bulk seed, like an import: Frappe otherwise stops at 60 new users an hour
	in_import, frappe.flags.in_import = frappe.flags.in_import, True
	try:
		_create_all(password, created)
	finally:
		frappe.flags.in_import = in_import
	frappe.db.commit()
	print(f"{len(created)} demo users created; password: {password}")
	for email in created:
		print(f"  {email}")
	return created


def _create_all(password: str, created: list[str]):
	for position in all_positions():
		if not frappe.db.exists("Role Profile", position):
			continue
		email = email_for(position)
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
			if position not in {r.role_profile for r in user.role_profiles}:
				user.append("role_profiles", {"role_profile": position})
				user.save(ignore_permissions=True)
			continue
		new_user(email=email, first_name=position, last_name="(demo)", password=password, positions=[position])
		created.append(email)


def new_user(email: str, first_name: str, last_name: str, password: str, positions: list[str]):
	"""A user built from frappe.new_doc, so it has every field default (enabled, sessions, …): the bulk
	seed runs with frappe.flags.in_import, under which insert() itself skips defaults"""
	user = frappe.new_doc("User")
	user.update(
		{
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"send_welcome_email": 0,
			"new_password": password,
		}
	)
	for position in positions:
		user.append("role_profiles", {"role_profile": position})
	user.insert(ignore_permissions=True)
	return user
