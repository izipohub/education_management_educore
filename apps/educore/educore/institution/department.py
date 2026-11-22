"""Rules for the university's units in ERPNext's Department tree (doc_events on Department)"""

import frappe
from frappe import _

from educore.setup.custom_fields import ALLOWED_PARENTS, GROUP_UNIT_TYPES


def validate(doc, method=None):
	unit_type = doc.get("educore_unit_type")
	if not unit_type:
		# ERPNext's own departments and anything not yet classified are left as they are
		return

	if doc.get("educore_unit_code"):
		doc.educore_unit_code = doc.educore_unit_code.strip().upper()

	if unit_type in GROUP_UNIT_TYPES:
		doc.is_group = 1

	parent_type = ""
	if doc.parent_department:
		parent_type = frappe.db.get_value("Department", doc.parent_department, "educore_unit_type") or ""
	if parent_type not in ALLOWED_PARENTS[unit_type]:
		allowed = [p or _("the top of the tree") for p in ALLOWED_PARENTS[unit_type]]
		frappe.throw(
			_("A {0} must sit under {1}, not under {2}").format(
				_(unit_type), _(" or ").join(allowed), doc.parent_department
			)
		)

	campuses = [row.campus for row in doc.get("educore_campuses") or []]
	if len(campuses) != len(set(campuses)):
		frappe.throw(_("Each campus can be listed once"))
