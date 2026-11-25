"""Re-registration, for the Vue app: a returning student registers for the new year; the faculty officer approves.

The student's registration is found from the session (Student.user), never from a name the browser sends, and
written by these functions after their checks (the student needs no permission on Program Enrollment). Officers
see registrations through frappe.get_list, so their campus and faculty User Permissions apply; approving submits
the enrolment as a system action (its invoice is posted to accounts officers cannot write to).
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate

from educore.registration import rules

REVIEW_ROLES = ("Faculty Officer", "Registrar", "System Manager")


# --- the student ---------------------------------------------------------------------------------------


def _student() -> str:
	student = frappe.db.get_value("Student", {"user": frappe.session.user}) if frappe.session.user != "Guest" else None
	if not student:
		frappe.throw(_("Sign in with your student account"), frappe.PermissionError)
	return student


def _registration(student: str, academic_year: str):
	name = frappe.db.get_value(
		"Program Enrollment", {"student": student, "academic_year": academic_year, "docstatus": ("<", 2)}, "name"
	)
	return frappe.get_doc("Program Enrollment", name) if name else None


def _state(student: str) -> dict:
	period = rules.current_period()
	history = rules.enrolments(student)
	latest = history[0] if history else None
	standing, standing_note = frappe.db.get_value("Student", student, ["educore_academic_standing", "educore_standing_note"])
	result = {
		"period": None,
		"standing": standing,
		"standing_note": standing_note,
		"programme": latest.program if latest else None,
		"offering": latest.educore_programme_offering if latest else None,
	}
	if not period or not latest:
		return result
	registration = _registration(student, period.academic_year)
	year = rules.year_of_study(student, period.academic_year)
	offering = latest.educore_programme_offering
	result.update(
		{
			"period": {
				"academic_year": period.academic_year,
				"opens_on": str(period.opens_on),
				"closes_on": str(period.closes_on),
				"late_until": str(period.late_until) if period.late_until else None,
				"late_fee": period.late_fee,
				"state": rules.period_state(period),
			},
			"year_of_study": year,
			# each course with what is open to this student: passed, a repeat, blocked by a prerequisite, open
			"courses": _with_states(student, latest.program, year),
			"max_credits": rules.settings().max_credits or 0,
			"fees": {
				"year": rules.year_fees(offering, period.academic_year),
				"outstanding": rules.outstanding(student, period.academic_year),
				"deposit_required": rules.deposit_required(offering, period.academic_year),
				"paid_in_advance": rules.paid_in_advance(student),
			},
			"blockers": rules.blockers(student, offering, period),
			"registration": _serialise(registration) if registration else None,
		}
	)
	return result


def _with_states(student: str, program: str, year: int) -> list[dict]:
	states = rules.course_states(student, program, year)
	names = {c["course"]: c["course_name"] for c in rules.curriculum(program)}
	out = []
	for c in rules.curriculum(program):
		state = states.get(c["course"], {"state": rules.OPEN, "missing": []})
		out.append({**c, "state": state["state"], "missing": [names.get(m, m) for m in state["missing"]]})
	return out


def _serialise(doc) -> dict:
	return {
		"name": doc.name,
		"status": rules.APPROVED if doc.docstatus == 1 else (doc.get("educore_registration_status") or rules.DRAFT),
		"courses": [row.course for row in doc.courses],
		"submitted_on": str(doc.educore_submitted_on) if doc.get("educore_submitted_on") else None,
		"late": bool(doc.get("educore_late")),
		"review_note": doc.get("educore_review_note"),
		"online": bool(doc.get("educore_registration_status")),
	}


@frappe.whitelist(methods=["GET"])
def status() -> dict:
	return _state(_student())


def _draft(student: str):
	"""This year's registration to edit: a new one, a draft, or one returned by the faculty"""
	period = rules.current_period()
	if not period or rules.period_state(period) not in ("open", "late"):
		frappe.throw(_("Registration is not open"))
	history = rules.enrolments(student)
	if not history:
		frappe.throw(_("Only returning students register here"))
	doc = _registration(student, period.academic_year)
	if doc and (doc.docstatus == 1 or doc.get("educore_registration_status") == rules.SUBMITTED):
		frappe.throw(_("Your registration is submitted and can no longer be changed"))
	if doc and not doc.get("educore_registration_status"):
		frappe.throw(_("The Registry has already registered you for {0}").format(period.academic_year))
	if not doc:
		latest = history[0]
		doc = frappe.new_doc("Program Enrollment")
		doc.update(
			{
				"student": student,
				"program": latest.program,
				"educore_programme_offering": latest.educore_programme_offering,
				"academic_year": period.academic_year,
				"academic_term": frappe.db.get_value(
					"Academic Term", {"academic_year": period.academic_year}, "name", order_by="term_start_date asc"
				),
				"enrollment_date": max(getdate(nowdate()), getdate(frappe.db.get_value("Academic Year", period.academic_year, "year_start_date"))),
				"educore_registration_status": rules.DRAFT,
			}
		)
	doc.educore_year_of_study = rules.year_of_study(student, period.academic_year)
	return doc, period


@frappe.whitelist(methods=["POST"])
def save(courses: list | str) -> dict:
	"""The courses chosen for the year (a draft until submitted)"""
	student = _student()
	doc, _period = _draft(student)
	chosen = list(dict.fromkeys(frappe.parse_json(courses) if isinstance(courses, str) else courses))
	known = {c["course"]: c for c in rules.curriculum(doc.program)}
	doc.set("courses", [])
	for course in chosen:
		if course not in known:
			frappe.throw(_("{0} is not part of your programme").format(course))
		doc.append("courses", {"course": course, "course_name": known[course]["course_name"]})
	if doc.get("educore_registration_status") == rules.RETURNED:
		doc.educore_registration_status = rules.DRAFT
	doc.flags.ignore_permissions = True
	doc.save()
	return _state(student)


@frappe.whitelist(methods=["POST"])
def submit() -> dict:
	student = _student()
	doc, period = _draft(student)
	if doc.is_new():
		frappe.throw(_("Choose your courses first"))
	problems = rules.blockers(student, doc.educore_programme_offering, period)
	if problems:
		frappe.throw(_("You cannot register yet:") + "<br>" + "<br>".join(f"• {p}" for p in problems))
	rules.check_courses(doc.program, doc.educore_year_of_study, [row.course for row in doc.courses], doc.student)
	doc.educore_registration_status = rules.SUBMITTED
	doc.educore_submitted_on = now_datetime()
	doc.educore_late = 1 if rules.period_state(period) == "late" else 0
	doc.educore_review_note = None
	doc.flags.ignore_permissions = True
	doc.save()
	doc.add_comment("Info", _("Registration submitted online"))
	if not rules.settings().approval_needed:
		_approve(doc)
	return _state(student)


# --- the faculty officer -------------------------------------------------------------------------------


FIELDS = [
	"name",
	"student",
	"student_name",
	"program",
	"educore_programme_offering as offering",
	"campus",
	"academic_year",
	"educore_year_of_study as year_of_study",
	"educore_registration_status as status",
	"educore_submitted_on as submitted_on",
	"educore_late as late",
	"educore_review_note as review_note",
]


def _require_reviewer():
	if not set(frappe.get_roles()) & set(REVIEW_ROLES):
		frappe.throw(_("Only faculty officers and the Registrar approve registrations"), frappe.PermissionError)


def _reviewable(name: str):
	_require_reviewer()
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("read")  # campus and faculty scope
	if doc.docstatus != 0 or doc.get("educore_registration_status") != rules.SUBMITTED:
		frappe.throw(_("This registration is not waiting for approval"))
	return doc


@frappe.whitelist(methods=["GET"])
def queue(status: str = rules.SUBMITTED, academic_year: str | None = None) -> dict:
	_require_reviewer()
	if status not in (rules.SUBMITTED, rules.RETURNED, rules.APPROVED):
		frappe.throw(_("Unknown status {0}").format(status))
	period = rules.current_period()
	academic_year = academic_year or (period.academic_year if period else None)

	def rows(state):
		filters = {"educore_registration_status": ("is", "set"), "academic_year": academic_year}
		if state == rules.APPROVED:
			filters["docstatus"] = 1
		else:
			filters.update({"docstatus": 0, "educore_registration_status": state})
		return frappe.get_list("Program Enrollment", filters=filters, fields=FIELDS, order_by="educore_submitted_on asc", limit=500)

	return {
		"academic_year": academic_year,
		"rows": [_queue_row(row, approved=status == rules.APPROVED) for row in rows(status)],
		"counts": {s: len(rows(s)) for s in (rules.SUBMITTED, rules.RETURNED, rules.APPROVED)},
	}


def _queue_row(row, approved: bool) -> dict:
	"""A registration with its courses, credits and the student's standing"""
	doc = frappe.get_doc("Program Enrollment", row.name)
	when = rules.semesters(doc.program)
	states = rules.course_states(row.student, doc.program, doc.get("educore_year_of_study") or 1)
	row["courses"] = sorted(
		(
			{
				"course": c.course,
				"course_name": c.course_name,
				"credits": rules.credits(c.course),
				"semester": when.get(c.course, "Year"),
				"repeat": states.get(c.course, {}).get("state") == rules.REPEAT,
			}
			for c in doc.courses
		),
		key=lambda c: (rules.SEMESTER_ORDER.get(c["semester"], 9), c["course_name"]),
	)
	row["credits"] = sum(c["credits"] for c in row["courses"])
	row["standing"] = frappe.db.get_value("Student", row.student, "educore_academic_standing")
	if approved:
		row["status"] = rules.APPROVED
	return row


@frappe.whitelist(methods=["GET"])
def registration(name: str) -> dict:
	"""One registration in the approval queue (campus and faculty scope apply)"""
	_require_reviewer()
	rows = frappe.get_list(
		"Program Enrollment",
		filters={"name": name, "educore_registration_status": ("is", "set")},
		fields=[*FIELDS, "docstatus"],
		limit=1,
	)
	if not rows:
		frappe.throw(_("This registration is not in your approval queue"), frappe.DoesNotExistError)
	row = rows[0]
	return _queue_row(row, approved=row.pop("docstatus") == 1)


def _approve(doc):
	"""Submitting the enrolment is a system action (it creates course enrolments and the year's invoice, which
	neither students nor faculty officers write themselves); who approved is recorded"""
	from educore.finance.student_fees import _as_system

	doc.educore_registration_status = rules.APPROVED
	doc.educore_reviewed_by = frappe.session.user
	doc.flags.ignore_permissions = True
	with _as_system():
		doc.submit()
	doc.add_comment("Workflow", _("Registration approved"))
	from educore.academics import notify

	notify.send(doc.student, "registration_approved", doc, academic_year=doc.academic_year, programme=doc.program)
	# back from interrupted studies (educore.api.v1.studies_requests)
	back_in = frappe.db.get_value("Student", doc.student, "educore_interrupted_until")
	if back_in and str(doc.academic_year) >= str(back_in):
		frappe.db.set_value("Student", doc.student, {"educore_interrupted_until": None, "educore_left_reason": None, "educore_left_on": None})


@frappe.whitelist(methods=["POST"])
def approve(name: str) -> dict:
	doc = _reviewable(name)
	# what blocked the student when they submitted may have changed since: the officer sees it, but decides
	_approve(doc)
	return {"name": doc.name, "status": rules.APPROVED}


@frappe.whitelist(methods=["POST"])
def return_registration(name: str, note: str) -> dict:
	"""Back to the student with a note, e.g. a course to add"""
	doc = _reviewable(name)
	if not (note or "").strip():
		frappe.throw(_("Tell the student what to change"))
	doc.educore_registration_status = rules.RETURNED
	doc.educore_review_note = note.strip()
	doc.educore_reviewed_by = frappe.session.user
	doc.flags.ignore_permissions = True
	doc.save()
	doc.add_comment("Workflow", _("Registration returned: {0}").format(note.strip()))
	from educore.academics import notify

	notify.send(doc.student, "registration_returned", doc, academic_year=doc.academic_year, note=note.strip())
	return {"name": doc.name, "status": rules.RETURNED}
