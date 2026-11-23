"""Shared helpers for EduCore's tests"""

import frappe
from frappe.model.workflow import apply_workflow


def submitted(applicant):
	"""An application starts as a Draft; staff capturing a paper application submit it (workflow "Submit")"""
	return apply_workflow(applicant, "Submit")


def school_route() -> str | None:
	"""The university's route for school leavers (judged on school results), whatever it calls it: the first
	open one in its order"""
	return next(
		iter(
			frappe.get_all(
				"Admission Pathway",
				filters={"active": 1, "evidence": "School results", "level": "Undergraduate"},
				pluck="name",
				order_by="sort_order asc, name asc",
			)
		),
		None,
	)

