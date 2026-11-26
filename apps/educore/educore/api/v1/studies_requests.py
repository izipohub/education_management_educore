"""Interrupting or cancelling studies, or moving to another campus: the student asks, the Registry decides.

- Interruption: the student pauses and registers again from a later academic year (Student.educore_interrupted_until);
  registration is blocked until then.
- Cancellation: the student leaves; the Student is no longer active, and returning means applying again.

Either way the student comes off this year's class lists (their Course Enrollments for the year are removed; the
Teaching screen shows the lists as out of date) and the registration stays on record. What is owed or refunded is
Finance's to decide; the request's dates are on the student's record for them.

- Campus transfer: the same programme at another campus, from an academic year the student has not registered for
  yet. Once approved the student belongs to the new campus (its Registry and Finance), and registers there from that
  year (educore.registration.rules.offering_for).
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate

from educore.academics import notify
from educore.api.v1.registration import _student

DECIDE_ROLES = ("Registrar", "Registry Officer", "System Manager")
SUBMITTED, APPROVED, DECLINED = "Submitted", "Approved", "Declined"
INTERRUPTION, CANCELLATION, TRANSFER = "Interruption", "Cancellation", "Campus transfer"


def _serialise(doc) -> dict:
	return {
		"name": doc.name,
		"request_type": doc.request_type,
		"student": doc.student,
		"student_name": doc.student_name,
		"program": doc.program,
		"campus": doc.campus,
		"academic_year": doc.academic_year,
		"last_day": str(doc.last_day) if doc.last_day else None,
		"return_year": doc.return_year,
		"to_offering": doc.get("to_offering"),
		"to_campus": doc.get("to_campus"),
		"from_year": doc.get("from_year"),
		"reason": doc.reason,
		"status": doc.status,
		"submitted_on": str(doc.submitted_on) if doc.submitted_on else None,
		"reviewed_on": str(doc.reviewed_on) if doc.reviewed_on else None,
		"review_note": doc.review_note,
	}


def _years_after(academic_year: str | None) -> list[str]:
	years = frappe.get_all("Academic Year", pluck="name", order_by="name asc")
	return [y for y in years if not academic_year or str(y) > str(academic_year)]


def _transfer_years(student: str) -> list[str]:
	"""Years a transfer can start from: open for registration or later, and not registered for already"""
	from educore.registration import rules

	period = rules.current_period()
	registered = set(frappe.get_all("Program Enrollment", filters={"student": student, "docstatus": ("<", 2)}, pluck="academic_year"))
	first = period.academic_year if period else None
	years = frappe.get_all("Academic Year", pluck="name", order_by="name asc")
	return [y for y in years if (not first or str(y) >= str(first)) and y not in registered][:3]


def _transfer_offerings(student: str) -> list[dict]:
	"""The student's programme at the other campuses"""
	latest = _latest(student)
	if not latest:
		return []
	return frappe.get_all(
		"Programme Offering",
		filters={"program": latest.program, "campus": ("!=", latest.campus)},
		fields=["name", "campus", "mode_of_study"],
		order_by="campus asc, mode_of_study asc",
	)


def _latest(student: str):
	return frappe.db.get_value(
		"Program Enrollment",
		{"student": student, "docstatus": 1},
		["name", "program", "campus", "academic_year"],
		as_dict=True,
		order_by="academic_year desc",
	)


# --- the student ---------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def mine() -> dict:
	student = _student()
	enabled, completed, interrupted_until = frappe.db.get_value("Student", student, ["enabled", "educore_completed_on", "educore_interrupted_until"])
	latest = _latest(student)
	requests = [
		_serialise(frappe.get_doc("Studies Request", n))
		for n in frappe.get_all("Studies Request", filters={"student": student}, pluck="name", order_by="creation desc")
	]
	pending = any(r["status"] == SUBMITTED for r in requests)
	return {
		"requests": requests,
		"can_request": bool(enabled and latest and not completed and not interrupted_until and not pending),
		"academic_year": latest.academic_year if latest else None,
		"return_years": _years_after(latest.academic_year if latest else None),
		"interrupted_until": interrupted_until,
		"campus": latest.campus if latest else None,
		"transfer_offerings": _transfer_offerings(student) if latest else [],
		"transfer_years": _transfer_years(student) if latest else [],
	}


@frappe.whitelist(methods=["POST"])
def request(
	request_type: str,
	last_day: str | None = None,
	reason: str = "",
	return_year: str | None = None,
	to_offering: str | None = None,
	from_year: str | None = None,
) -> dict:
	student = _student()
	state = mine()
	if not state["can_request"]:
		frappe.throw(_("A request cannot be made now"))
	if request_type not in (INTERRUPTION, CANCELLATION, TRANSFER):
		frappe.throw(_("Choose interrupting or cancelling your studies, or moving campus"))
	if not (reason or "").strip():
		frappe.throw(_("Give the reason"))
	if request_type == TRANSFER:
		if to_offering not in {o.name for o in state["transfer_offerings"]}:
			frappe.throw(_("Choose your programme at the campus you move to"))
		if from_year not in state["transfer_years"]:
			frappe.throw(_("Choose the academic year you start at the new campus"))
		last_day = return_year = None
	elif not last_day or getdate(last_day) > getdate(nowdate()):
		frappe.throw(_("The last day attending cannot be in the future"))
	else:
		to_offering = from_year = None
	if request_type == INTERRUPTION:
		if return_year not in state["return_years"]:
			frappe.throw(_("Choose the academic year you return in"))
	elif request_type == CANCELLATION:
		return_year = None
	latest = _latest(student)
	frappe.get_doc(
		{
			"doctype": "Studies Request",
			"request_type": request_type,
			"student": student,
			"program": latest.program,
			"campus": latest.campus,
			"academic_year": latest.academic_year,
			"last_day": last_day,
			"return_year": return_year,
			"to_offering": to_offering,
			"from_year": from_year,
			"reason": reason.strip(),
			"status": SUBMITTED,
			"submitted_on": now_datetime(),
		}
	).insert(ignore_permissions=True)
	return mine()


# --- the Registry --------------------------------------------------------------------------------------


def _require():
	if not set(frappe.get_roles()) & set(DECIDE_ROLES):
		frappe.throw(_("Requests to interrupt or cancel studies are decided by the Registry"), frappe.PermissionError)


def _in_scope(students: list[str]) -> set[str]:
	if not students:
		return set()
	return set(frappe.get_list("Student", filters={"name": ("in", students)}, pluck="name", limit=0))


def _decidable(name: str):
	_require()
	doc = frappe.get_doc("Studies Request", name)
	if doc.student not in _in_scope([doc.student]):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if doc.status != SUBMITTED:
		frappe.throw(_("This request is decided already"))
	return doc


@frappe.whitelist(methods=["GET"])
def queue(status: str = SUBMITTED) -> dict:
	_require()
	if status not in (SUBMITTED, APPROVED, DECLINED):
		frappe.throw(_("Unknown status {0}").format(status))
	rows = frappe.get_all("Studies Request", fields=["name", "student", "status"], order_by="submitted_on asc")
	mine_ = _in_scope(list({r.student for r in rows}))
	rows = [r for r in rows if r.student in mine_]
	return {
		"rows": [_serialise(frappe.get_doc("Studies Request", r.name)) for r in rows if r.status == status],
		"counts": {s: sum(1 for r in rows if r.status == s) for s in (SUBMITTED, APPROVED, DECLINED)},
	}


def _apply(doc):
	"""Off this year's class lists; the Student marked interrupted or cancelled. A transfer: the student belongs to
	the new campus from now, and registers there from the year asked for"""
	if doc.request_type == TRANSFER:
		to_campus = frappe.db.get_value("Programme Offering", doc.to_offering, "campus")
		frappe.db.set_value("Student", doc.student, "campus", to_campus)
		frappe.get_doc("Student", doc.student).add_comment(
			"Info", _("Campus transfer approved: {0} from {1}, from {2}. {3}").format(to_campus, doc.campus, doc.from_year, doc.reason)
		)
		return
	registration = frappe.db.get_value("Program Enrollment", {"student": doc.student, "academic_year": doc.academic_year, "docstatus": 1})
	if registration:
		for name in frappe.get_all("Course Enrollment", filters={"program_enrollment": registration}, pluck="name"):
			frappe.delete_doc("Course Enrollment", name, force=True, ignore_permissions=True)
	values = {"educore_left_on": doc.last_day}
	if doc.request_type == INTERRUPTION:
		values.update({"educore_interrupted_until": doc.return_year, "educore_left_reason": _("Studies interrupted ({0})").format(doc.name)})
	else:
		values.update({"enabled": 0, "educore_left_reason": _("Studies cancelled ({0})").format(doc.name)})
	frappe.db.set_value("Student", doc.student, values)
	frappe.get_doc("Student", doc.student).add_comment(
		"Info", _("{0} approved: last day attending {1}. {2}").format(doc.request_type, frappe.utils.formatdate(doc.last_day), doc.reason)
	)


@frappe.whitelist(methods=["POST"])
def approve(name: str) -> dict:
	doc = _decidable(name)
	_apply(doc)
	doc.status = APPROVED
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.save(ignore_permissions=True)
	event = {INTERRUPTION: "interruption_approved", CANCELLATION: "cancellation_approved", TRANSFER: "transfer_approved"}[doc.request_type]
	notify.send(
		doc.student, event, doc, last_day=notify.date(doc.last_day), return_year=doc.return_year, to_campus=doc.get("to_campus"), from_year=doc.get("from_year")
	)
	return queue()


@frappe.whitelist(methods=["POST"])
def decline(name: str, note: str) -> dict:
	doc = _decidable(name)
	if not (note or "").strip():
		frappe.throw(_("Tell the student why"))
	doc.status = DECLINED
	doc.review_note = note.strip()
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.save(ignore_permissions=True)
	what = {
		INTERRUPTION: _("interrupt your studies"),
		CANCELLATION: _("cancel your studies"),
		TRANSFER: _("move to {0}").format(doc.get("to_campus")),
	}[doc.request_type]
	notify.send(doc.student, "studies_request_declined", doc, what=what, note=doc.review_note)
	return queue()


@frappe.whitelist(methods=["POST"])
def resume(student: str) -> dict:
	"""An interrupted student comes back early (the Registry): the interruption is lifted"""
	_require()
	if student not in _in_scope([student]):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.db.get_value("Student", student, "educore_interrupted_until"):
		frappe.throw(_("These studies are not interrupted"))
	frappe.db.set_value("Student", student, {"educore_interrupted_until": None, "educore_left_reason": None, "educore_left_on": None})
	frappe.get_doc("Student", student).add_comment("Info", _("Interruption lifted"))
	return {"student": student}
