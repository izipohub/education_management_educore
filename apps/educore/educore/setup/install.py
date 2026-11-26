"""After install and every migrate: EduCore's custom fields, roles and positions, and upstream read access"""

import frappe

from educore.academics import results as exam_results
from educore.academics import assessment_types, workload
from educore.access import desk, roles
from educore.admissions import pathways
from educore.registration import rules as registration
from educore.setup import custom_fields, permissions, workflows


def after_migrate():
	custom_fields.sync()
	roles.sync()
	permissions.sync()
	workflows.sync()
	desk.sync()
	pathways.ensure_defaults()
	registration.ensure_defaults()
	exam_results.ensure_defaults()
	workload.ensure_defaults()
	assessment_types.ensure_defaults()
	_fee_setup()
	_lecturers()
	_funding()


def _fee_setup():
	"""The student fee accounts and categories (new ones included), once the university is set up"""
	from educore.finance.student_fees import ensure_fee_setup

	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
	if company:
		ensure_fee_setup(company)


def _lecturers():
	"""Every lecturer login has its Instructor record (logins made before this existed included)"""
	from educore.academics.lecturers import sync_all

	if frappe.db.has_column("Instructor", "educore_user"):
		sync_all()


def _funding():
	"""The default funding routes, and the regional (SADC) countries for the application fee"""
	from educore.admissions import funding

	funding.ensure_defaults()
