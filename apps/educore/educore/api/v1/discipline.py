"""Disciplinary cases (educore.academics.discipline): reported by staff, handled by Student Affairs, appeals decided by
the Registrar, followed by the student from the hearing on.

Confidential: a case is seen by the Student Affairs Officers of the student's campus and by the Registrar; the person
who reported it is told it reached Student Affairs, nothing more. Who may report a student: a member of staff who may
read the student's record (their offices), or a lecturer who teaches them.
"""

import frappe
from frappe import _
from frappe.utils import flt

from educore.academics import discipline as d

HANDLE_ROLES = ("Student Affairs Officer", "System Manager")
APPEAL_ROLES = ("Registrar", "System Manager")
READ_ROLES = (*HANDLE_ROLES, *APPEAL_ROLES)


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _upload() -> tuple[bytes, str] | None:
	upload = frappe.request.files.get("file") if frappe.request and frappe.request.files else None
	return (upload.stream.read(), upload.filename) if upload and upload.filename else None


# --- reporting (any member of staff with the student in their work) ----------------------------------


def _may_report(student: str) -> bool:
	if "University Staff" not in frappe.get_roles() and not _has(("System Manager",)):
		return False
	if frappe.has_permission("Student", "read") and frappe.get_list("Student", filters={"name": student}, pluck="name", limit=1):
		return True
	from educore.academics.lecturers import instructors_of

	instructors = instructors_of(frappe.session.user)
	if not instructors:
		return False
	groups = frappe.get_all("Student Group Instructor", filters={"instructor": ("in", instructors), "parenttype": "Student Group"}, pluck="parent")
	return bool(groups) and bool(frappe.db.exists("Student Group Student", {"parent": ("in", groups), "student": student, "active": 1}))


@frappe.whitelist(methods=["POST"])
def report(student: str, incident_date: str, incident: str) -> dict:
	"""A report of misconduct (multipart, with optional "file" evidence), to Student Affairs"""
	if not _may_report(student):
		frappe.throw(_("You can report a student you teach or whose record you work with"), frappe.PermissionError)
	doc = d.report(student, incident_date, incident, _upload())
	return {"name": doc.name, "student_name": doc.student_name}


# --- Student Affairs and the Registrar ----------------------------------------------------------------


def _require(roles=READ_ROLES):
	if not _has(roles):
		frappe.throw(_("Disciplinary cases are Student Affairs'"), frappe.PermissionError)


def _in_scope(rows: list) -> list:
	"""Student Affairs: its campuses; the Registrar: every campus"""
	if _has(APPEAL_ROLES):
		return rows
	from educore.access.scope import campuses

	mine = campuses()
	return [r for r in rows if r.campus in mine]


def _case(name: str, roles=READ_ROLES):
	_require(roles)
	rows = _in_scope(frappe.get_all("Disciplinary Case", filters={"name": name}, fields=["name", "campus"]))
	if not rows:
		frappe.throw(_("This case is not on your campus"), frappe.PermissionError)
	return frappe.get_doc("Disciplinary Case", name)


def _serialise(doc, for_student: bool = False) -> dict:
	from educore.finance import charges

	shared = {
		"name": doc.name,
		"status": doc.status,
		"level": doc.level,
		"charge": doc.charge,
		"hearing_on": str(doc.hearing_on) if doc.hearing_on else None,
		"hearing_venue": doc.hearing_venue,
		"finding": doc.finding,
		"sanction": doc.sanction,
		"outcome": d.describe(doc) if doc.status in (d.DECIDED, d.APPEALED, d.CLOSED) else None,
		"decision_note": doc.decision_note,
		"decided_on": str(doc.decided_on) if doc.decided_on else None,
		"appeal_until": str(doc.appeal_until) if doc.appeal_until else None,
		"appeal_reason": doc.appeal_reason,
		"appealed_on": str(doc.appealed_on) if doc.appealed_on else None,
		"appeal_outcome": doc.appeal_outcome,
		"appeal_note": doc.appeal_note,
		"fine": flt(doc.fine),
		"fine_unpaid": charges.unpaid(doc.fine_invoice),
		"suspended_from": str(doc.suspended_from) if doc.suspended_from else None,
		"suspended_until": str(doc.suspended_until) if doc.suspended_until else None,
	}
	if for_student:
		return {**shared, "can_appeal": doc.status == d.DECIDED and bool(doc.appeal_until) and frappe.utils.getdate(doc.appeal_until) >= frappe.utils.getdate()}
	return {
		**shared,
		"student": doc.student,
		"student_name": doc.student_name,
		"campus": doc.campus,
		"reported_by": frappe.utils.get_fullname(doc.reported_by) if doc.reported_by else None,
		"reported_on": str(doc.reported_on) if doc.reported_on else None,
		"incident_date": str(doc.incident_date) if doc.incident_date else None,
		"incident": doc.incident,
		"evidence": bool(doc.evidence),
		"investigated_by": frappe.utils.get_fullname(doc.investigated_by) if doc.investigated_by else None,
		"investigation_note": doc.investigation_note,
		"committee": doc.committee,
		"hearing_note": doc.hearing_note,
		"decided_by": frappe.utils.get_fullname(doc.decided_by) if doc.decided_by else None,
		"appeal_decided_by": frappe.utils.get_fullname(doc.appeal_decided_by) if doc.appeal_decided_by else None,
		"earlier": frappe.db.count("Disciplinary Case", {"student": doc.student, "name": ("!=", doc.name), "finding": d.RESPONSIBLE}),
		"can_handle": _has(HANDLE_ROLES),
		"can_decide_appeal": _has(APPEAL_ROLES) and doc.status == d.APPEALED,
	}


@frappe.whitelist(methods=["GET"])
def cases() -> dict:
	_require()
	rows = _in_scope(
		frappe.get_all(
			"Disciplinary Case",
			fields=["name", "student", "student_name", "campus", "status", "level", "incident_date", "reported_on", "hearing_on", "sanction", "appealed_on"],
			order_by="reported_on asc",
			limit=0,
		)
	)
	for r in rows:
		for k in ("incident_date", "reported_on", "hearing_on", "appealed_on"):
			r[k] = str(r[k]) if r[k] else None
	return {"rows": rows, "appeal_days": d.appeal_days(), "can_set_rules": _has(APPEAL_ROLES), "can_handle": _has(HANDLE_ROLES)}


@frappe.whitelist(methods=["GET"])
def case(name: str) -> dict:
	return _serialise(_case(name))


@frappe.whitelist(methods=["POST"])
def investigate(name: str) -> dict:
	doc = _case(name, HANDLE_ROLES)
	d.investigate(doc)
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def dismiss(name: str, note: str) -> dict:
	doc = _case(name, HANDLE_ROLES)
	d.dismiss(doc, note)
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def schedule_hearing(name: str, charge: str, hearing_on: str, venue: str, committee: str | None = None, note: str | None = None) -> dict:
	doc = _case(name, HANDLE_ROLES)
	d.schedule_hearing(doc, charge, hearing_on, venue, committee, note)
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def decide(
	name: str, finding: str, reasons: str, sanction: str | None = None, fine: float | str = 0,
	suspended_from: str | None = None, suspended_until: str | None = None, hearing_note: str | None = None,
) -> dict:
	doc = _case(name, HANDLE_ROLES)
	d.decide(doc, finding, sanction, reasons, flt(fine), suspended_from, suspended_until, hearing_note)
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def decide_appeal(
	name: str, outcome: str, note: str, sanction: str | None = None, fine: float | str = 0,
	suspended_from: str | None = None, suspended_until: str | None = None,
) -> dict:
	doc = _case(name, APPEAL_ROLES)
	d.decide_appeal(doc, outcome, note, sanction, flt(fine), suspended_from, suspended_until)
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def save_rules(appeal_days: int | str) -> dict:
	_require(APPEAL_ROLES)
	days = frappe.utils.cint(appeal_days)
	if not 1 <= days <= 60:
		frappe.throw(_("Between 1 and 60 days"))
	frappe.db.set_single_value("Discipline Settings", "appeal_days", days)
	return cases()


@frappe.whitelist(methods=["GET"])
def evidence(name: str):
	doc = _case(name)
	if not doc.evidence:
		frappe.throw(_("No evidence attached"), frappe.DoesNotExistError)
	file = frappe.get_doc("File", {"file_url": doc.evidence})
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"


# --- the student --------------------------------------------------------------------------------------


def _student() -> str:
	name = frappe.db.get_value("Student", {"user": frappe.session.user, "enabled": 1})
	if not name:
		frappe.throw(_("This page is for students."), frappe.PermissionError)
	return name


@frappe.whitelist(methods=["GET"])
def mine() -> list[dict]:
	"""The student's cases from the hearing or decision on (never the investigation)"""
	student = _student()
	return [
		_serialise(frappe.get_doc("Disciplinary Case", n), for_student=True)
		for n in frappe.get_all("Disciplinary Case", filters={"student": student, "status": ("in", d.SEEN_BY_STUDENT)}, pluck="name", order_by="creation desc")
	]


@frappe.whitelist(methods=["POST"])
def appeal(name: str, reason: str) -> list[dict]:
	student = _student()
	doc = frappe.get_doc("Disciplinary Case", name)
	if doc.student != student:
		frappe.throw(_("This is not your case"), frappe.PermissionError)
	d.appeal(doc, reason)
	return mine()
