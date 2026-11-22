"""Rules for Education's Program and Course in a university (doc_events)"""

import frappe
from frappe import _

from educore.setup.custom_fields import ACADEMIC_UNIT_TYPES


def _check_academic_unit(doc):
	if not doc.department:
		return
	unit_type = frappe.db.get_value("Department", doc.department, "educore_unit_type")
	if unit_type not in ACADEMIC_UNIT_TYPES:
		frappe.throw(
			_("{0} must belong to a faculty, school or academic department, not {1}").format(
				_(doc.doctype), doc.department
			)
		)


def _check_nqf_level(doc):
	level = doc.get("educore_nqf_level")
	if level and not 1 <= level <= 10:
		frappe.throw(_("NQF level must be between 1 and 10"))


def validate_program(doc, method=None):
	if doc.get("educore_programme_code"):
		doc.educore_programme_code = doc.educore_programme_code.strip().upper()
	_check_academic_unit(doc)
	_check_nqf_level(doc)
	if (doc.get("educore_credits") or 0) < 0 or (doc.get("educore_duration_years") or 0) < 0:
		frappe.throw(_("Credits and duration cannot be negative"))


def validate_course(doc, method=None):
	if doc.get("educore_course_code"):
		doc.educore_course_code = doc.educore_course_code.strip().upper()
	_check_academic_unit(doc)
	_check_nqf_level(doc)
	if (doc.get("educore_credits") or 0) < 0:
		frappe.throw(_("Credits cannot be negative"))
