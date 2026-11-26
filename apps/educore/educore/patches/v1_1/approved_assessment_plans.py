"""Assessment plans are approved by the Head of Department before scores go in. A module that already had its
gradebook keeps working: its plan counts as approved."""

import frappe


def execute():
	for name in frappe.get_all("Mark Sheet Assessment", filters={"parenttype": "Mark Sheet"}, pluck="parent", distinct=True):
		if not frappe.db.get_value("Mark Sheet", name, "plan_status"):
			frappe.db.set_value("Mark Sheet", name, "plan_status", "Approved", update_modified=False)
