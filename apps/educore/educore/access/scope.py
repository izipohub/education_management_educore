"""Which campuses a member of staff works across.

Campus scope comes from the user's User Permissions on Campus (none: every campus). A head of department or a dean
works across their department or faculty on every campus, even when they also lecture on one campus: the Campus
permission their teaching gives them must not narrow their department's classes and marks.
"""

import frappe

#: positions whose scope is a department or faculty on every campus
UNIT_WIDE_ROLES = {"Head of Department", "Dean", "System Manager"}


def campuses() -> set[str]:
	if set(frappe.get_roles()) & UNIT_WIDE_ROLES:
		return set(frappe.get_all("Campus", pluck="name"))
	return set(frappe.get_list("Campus", pluck="name", limit=0))
