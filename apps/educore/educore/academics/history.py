"""A student's status history: what happened to their studies and when, newest first.

Read from the records that hold each event, so it cannot disagree with them: the admission, every approved
registration, approved interruptions, cancellations and campus transfers (and an interruption lifted early), financial
holds placed and lifted, disciplinary decisions and appeals, and the completion the Senate approved.
"""

import frappe
from frappe import _
from frappe.utils import getdate


def _event(date, event: str, detail: str | None = None, kind: str = "info") -> dict:
	return {"date": str(getdate(date)) if date else None, "event": event, "detail": detail, "kind": kind}


def of_student(student: str) -> list[dict]:
	doc = frappe.get_doc("Student", student)
	events = []

	if doc.student_applicant:
		applied = frappe.db.get_value("Student Applicant", doc.student_applicant, ["program", "campus"], as_dict=True) or {}
		events.append(
			_event(doc.joining_date or doc.creation, _("Admitted"), ", ".join(x for x in (applied.get("program"), applied.get("campus")) if x), "start")
		)
	elif doc.joining_date:
		events.append(_event(doc.joining_date, _("Joined"), None, "start"))

	for pe in frappe.get_all(
		"Program Enrollment",
		filters={"student": student, "docstatus": 1},
		fields=["academic_year", "program", "campus", "educore_mode_of_study", "educore_year_of_study", "enrollment_date"],
	):
		where = ", ".join(x for x in (pe.program, pe.campus, pe.educore_mode_of_study) if x)
		year = _(" (year {0})").format(pe.educore_year_of_study) if pe.educore_year_of_study else ""
		events.append(_event(pe.enrollment_date, _("Registered for {0}{1}").format(pe.academic_year, year), where, "registration"))

	for r in frappe.get_all(
		"Studies Request",
		filters={"student": student, "status": "Approved"},
		fields=["request_type", "last_day", "return_year", "to_campus", "campus", "from_year", "reviewed_on", "reason"],
	):
		if r.request_type == "Interruption":
			events.append(
				_event(r.last_day or r.reviewed_on, _("Studies interrupted"), _("Returning in {0}. {1}").format(r.return_year, r.reason), "pause")
			)
		elif r.request_type == "Cancellation":
			events.append(_event(r.last_day or r.reviewed_on, _("Studies cancelled"), r.reason, "end"))
		else:
			events.append(
				_event(r.reviewed_on, _("Moved to {0}").format(r.to_campus), _("From {0}, registering there from {1}. {2}").format(r.campus, r.from_year, r.reason), "move")
			)
	for c in frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Student", "reference_name": student, "comment_type": "Info", "content": "Interruption lifted"},
		fields=["creation"],
	):
		events.append(_event(c.creation, _("Returned early from an interruption"), None, "registration"))

	from educore.academics import discipline

	for c in frappe.get_all(
		"Disciplinary Case",
		filters={"student": student, "status": ("in", (discipline.DECIDED, discipline.APPEALED, discipline.CLOSED))},
		fields=["name", "finding", "sanction", "fine", "suspended_from", "suspended_until", "decided_on", "appeal_outcome", "appeal_decided_on"],
	):
		if c.finding == discipline.RESPONSIBLE or c.appeal_outcome:
			kind = "hold" if c.sanction in (discipline.SUSPENSION, discipline.EXPULSION) else "info"
			events.append(_event(c.decided_on, _("Disciplinary decision"), discipline.describe(frappe._dict(c)) if not c.appeal_outcome else None, kind))
		if c.appeal_outcome:
			events.append(_event(c.appeal_decided_on, _("Disciplinary appeal {0}").format(_(c.appeal_outcome).lower()), discipline.describe(frappe._dict(c)), "info"))
	for h in frappe.get_all("Student Hold", filters={"student": student}, fields=["reason", "placed_on", "status", "lifted_on", "lift_note"]):
		events.append(_event(h.placed_on, _("Financial hold placed"), h.reason, "hold"))
		if h.status == "Lifted":
			events.append(_event(h.lifted_on, _("Financial hold lifted"), h.lift_note, "info"))

	if doc.get("educore_completed_on"):
		events.append(
			_event(
				doc.educore_completed_on,
				_("Completed {0}").format(doc.get("educore_completed_programme") or _("the programme")),
				_("Approved by the {0}").format(doc.educore_completion_reference) if doc.get("educore_completion_reference") else None,
				"end",
			)
		)
	return sorted(events, key=lambda e: e["date"] or "", reverse=True)
