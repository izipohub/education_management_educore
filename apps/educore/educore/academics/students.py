"""Applicants, students and enrolments on programme offerings (doc_events on Education's DocTypes).

The offering carries the campus, mode of study and faculty/department into each record, so campus and
faculty User Permissions apply to applicants, students and enrolments without extra code. Education's own
"Enroll" action (education.education.api.enroll_student) keeps working: the offering and campus follow
the applicant into the Student and the Program Enrollment.
"""

import frappe
from frappe import _


def _offering(name):
	return frappe.get_cached_doc("Programme Offering", name) if name else None


def validate_applicant(doc, method=None):
	from educore.admissions import application

	status = doc.application_status or "Draft"
	if status == "Draft":
		# an online application being filled in: up to three ranked choices, the first under decision
		application.tidy_draft(doc)
	# points and eligibility are always recomputed, so neither can be typed in
	application.assess(doc)
	from educore.admissions.fees import set_fee

	set_fee(doc)

	offering = _offering(doc.get("educore_programme_offering"))
	if not offering:
		if status == "Draft":
			return
		frappe.throw(_("Choose the programme offering: the programme, campus and mode of study applied for"))
	doc.program = offering.program
	doc.campus = offering.campus
	doc.educore_mode_of_study = offering.mode_of_study
	if doc.is_new() and not offering.is_active:
		frappe.throw(_("{0} is not taking applications").format(offering.name))
	if not doc.is_new() and doc.has_value_changed("application_status"):
		before = doc.get_doc_before_save()
		# an online application must be complete to submit; a paper application staff capture was checked in person
		if before and before.application_status == "Draft" and status == "Applied" and doc.get("educore_applicant_user"):
			application.check_submission(doc)
		_record_decision(doc, offering)


#: Decisions that need a written reason, and the decisions that are recorded with who and when
NEEDS_REASON = ("Rejected",)
DECISIONS = ("Approved", "Rejected")


def _record_decision(doc, offering):
	status = doc.application_status
	if status == "Approved":
		from educore.admissions.application import decision_blockers

		blockers = decision_blockers(doc)
		if blockers:
			frappe.throw(_("Not ready to approve:") + "<br>" + "<br>".join(f"• {b}" for b in blockers))
		_check_intake_capacity(doc, offering)
		from educore.admissions import offers

		offers.on_approved(doc)
	if status in NEEDS_REASON and not (doc.get("educore_decision_reason") or "").strip():
		frappe.throw(_("Write the reason in Decision Notes before rejecting the application or withdrawing the offer"))
	if status in DECISIONS:
		doc.educore_decided_by = frappe.session.user
		doc.educore_decided_on = frappe.utils.now_datetime()
	elif status == "Applied":
		# reconsidered: the old decision no longer stands, and a new rejection needs a new reason;
		# the timeline keeps the history
		doc.educore_decided_by = None
		doc.educore_decided_on = None
		doc.educore_decision_reason = None
		from educore.admissions import offers

		offers.on_reconsidered(doc)


def _check_intake_capacity(doc, offering):
	if not offering.intake_capacity:
		return
	taken = frappe.db.count(
		"Student Applicant",
		{
			"educore_programme_offering": offering.name,
			"academic_year": doc.academic_year,
			"application_status": ("in", ("Approved", "Admitted")),
			"name": ("!=", doc.name),
		},
	)
	if taken >= offering.intake_capacity:
		frappe.throw(
			_("{0} is full for {1}: all {2} places are offered. Withdraw an offer or raise the intake capacity first.").format(
				offering.name, doc.academic_year, offering.intake_capacity
			)
		)


def validate_student(doc, method=None):
	if not doc.get("campus") and doc.student_applicant:
		doc.campus = frappe.db.get_value("Student Applicant", doc.student_applicant, "campus")


def validate_enrollment(doc, method=None):
	if not doc.get("educore_programme_offering"):
		doc.educore_programme_offering = _offering_from_application(doc)
	offering = _offering(doc.get("educore_programme_offering"))
	if not offering:
		frappe.throw(_("Choose the programme offering the student is enrolled on"))
	if doc.program and doc.program != offering.program:
		frappe.throw(_("{0} is an offering of {1}, not of {2}").format(offering.name, offering.program, doc.program))
	doc.program = offering.program
	doc.campus = offering.campus
	doc.educore_mode_of_study = offering.mode_of_study
	doc.department = offering.department


def on_enrollment_submit(doc, method=None):
	# the student's faculty/department follows their latest enrolment, so faculty users see them;
	# a student without a home campus takes the campus of their first enrolment
	values = {"department": doc.department}
	if not frappe.db.get_value("Student", doc.student, "campus"):
		values["campus"] = doc.campus
	frappe.db.set_value("Student", doc.student, values)

	# the year's fees, from the offering's fee structure
	from educore.finance.student_fees import invoice_enrollment

	invoice_enrollment(doc)


def _offering_from_application(doc):
	"""The offering the student applied for, when this enrolment is on the same programme"""
	applicant = frappe.db.get_value("Student", doc.student, "student_applicant")
	if not applicant:
		return None
	offering, program = frappe.db.get_value("Student Applicant", applicant, ["educore_programme_offering", "program"])
	return offering if program == doc.program else None
