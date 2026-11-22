"""Shared helpers for EduCore's tests"""

from frappe.model.workflow import apply_workflow


def submitted(applicant):
	"""An application starts as a Draft; staff capturing a paper application submit it (workflow "Submit")"""
	return apply_workflow(applicant, "Submit")
