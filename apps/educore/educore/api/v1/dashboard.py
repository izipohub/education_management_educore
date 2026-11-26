"""The staff home: the numbers each position needs, for the campuses and faculties the user works on.

Every figure comes through frappe.get_list (or get_all only after a permission check), so campus and faculty
User Permissions apply: an Oshakati officer's dashboard counts Oshakati only. A section appears only for the roles
it concerns, and only when the user may read what it counts.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, getdate, nowdate

ADMISSIONS = ("Admissions Officer", "Registrar", "Campus Director", "Executive Management")
ENROLMENT = ("Registry Officer", "Registrar", "Campus Director", "Executive Management")
REGISTRATION = ("Faculty Officer", "Registrar", "Dean", "Head of Department", "Campus Director", "Executive Management")
FEES = ("Bursar", "Finance Officer", "Student Fees Officer", "Cashier", "Executive Management", "Campus Director")


def _has(roles: tuple) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _count(doctype: str, filters: dict) -> int:
	return len(frappe.get_list(doctype, filters=filters, pluck="name", limit=0))


def _by(doctype: str, field: str, filters: dict) -> list[dict]:
	"""Counts per value of a field, largest first"""
	rows = frappe.get_list(doctype, filters=filters, fields=[field, {"COUNT": "*", "as": "count"}], group_by=field, limit=0)
	return sorted(({"label": r[field] or "Not set", "value": r["count"]} for r in rows), key=lambda r: -r["value"])


def _intake_year() -> str | None:
	"""The newest academic year with applications this user can see"""
	years = frappe.get_list("Student Applicant", pluck="academic_year", distinct=True, limit=0)
	return max((y for y in years if y), default=None)


def _in_scope(filters: dict) -> dict:
	"""The filters, narrowed to the campus chosen on the dashboard (stats() sets it for this request)"""
	campus = getattr(frappe.local, "educore_dashboard_campus", None)
	return {**filters, "campus": campus} if campus else filters


@frappe.whitelist(methods=["GET"])
def stats(campus: str | None = None) -> dict:
	# the campuses this user may see (their User Permissions); a campus outside them is refused
	campuses = frappe.get_list("Campus", pluck="name", order_by="name asc", limit=0)
	if campus and campus not in campuses:
		frappe.throw(_("You do not work on {0}").format(campus), frappe.PermissionError)
	frappe.local.educore_dashboard_campus = campus or None

	sections = {}
	# the student figures for the student offices (a lecturer reads their own students on My modules)
	from educore.api.v1.student_records import RECORD_ROLES

	if _has((*RECORD_ROLES, *ADMISSIONS, *ENROLMENT)) and frappe.has_permission("Student", "read"):
		sections["students"] = _students()
	if _has(ADMISSIONS) and frappe.has_permission("Student Applicant", "read"):
		sections["admissions"] = _admissions()
	if _has(ENROLMENT) and frappe.has_permission("Student Applicant", "read"):
		sections["enrolment"] = _enrolment()
	if _has(REGISTRATION) and frappe.has_permission("Program Enrollment", "read"):
		sections["registration"] = _registration()
	if _has(FEES) and frappe.has_permission("Sales Invoice", "read"):
		sections["fees"] = _fees()
	return {
		"today": nowdate(),
		"campus": campus,
		"campuses": campuses,
		"sections": sections,
		# what is waiting for this person, from every queue their positions work on
		"work": _work(),
		# a lecturer's lessons today, each with its register
		"lessons": _lessons_today(),
	}


def _students() -> dict:
	filters = _in_scope({"enabled": 1})
	return {
		"total": _count("Student", filters),
		"by_campus": _by("Student", "campus", filters),
		"by_gender": _by("Student", "gender", filters),
	}


def _by_month(rows: list, months: int = 12) -> list[dict]:
	"""Counts per calendar month for the last `months` months, oldest first, empty months included"""
	today = getdate(nowdate())
	keys = [getdate(add_months(today, -i)).strftime("%Y-%m") for i in range(months - 1, -1, -1)]
	counts = dict.fromkeys(keys, 0)
	for day in rows:
		key = getdate(day).strftime("%Y-%m") if day else None
		if key in counts:
			counts[key] += 1
	return [{"label": key, "value": value} for key, value in counts.items()]


def _admissions() -> dict:
	year = _intake_year()
	base = _in_scope({"academic_year": year} if year else {})
	submitted = {**base, "application_status": ("!=", "Draft")}
	applications = frappe.get_list(
		"Student Applicant",
		filters=submitted,
		fields=["application_date", "program", "educore_pathway as pathway", "educore_applicant_user as online"],
		limit=0,
	)
	programmes: dict[str, int] = {}
	for row in applications:
		if row.program:
			programmes[row.program] = programmes.get(row.program, 0) + 1
	pathway_counts: dict[str, int] = {}
	for row in applications:
		key = row.pathway or _("Not recorded")
		pathway_counts[key] = pathway_counts.get(key, 0) + 1
	online = sum(1 for r in applications if r.online)
	status = {r["label"]: r["value"] for r in _by("Student Applicant", "application_status", base)}
	online_waiting = {**base, "application_status": "Applied", "educore_applicant_user": ("is", "set")}
	offerings = {}
	for row in frappe.get_list(
		"Student Applicant",
		filters={**base, "application_status": ("in", ("Applied", "Approved", "Admitted"))},
		fields=["educore_programme_offering as offering", "application_status as status"],
		limit=0,
	):
		if row.offering:
			entry = offerings.setdefault(row.offering, {"label": row.offering, "applied": 0, "taken": 0})
			entry["taken" if row.status in ("Approved", "Admitted") else "applied"] += 1
	for entry in offerings.values():
		entry["capacity"] = frappe.db.get_value("Programme Offering", entry["label"], "intake_capacity") or 0
	return {
		"academic_year": year,
		"pipeline": [
			{"label": "Submitted", "value": status.get("Applied", 0)},
			{"label": "Offered", "value": status.get("Approved", 0)},
			{"label": "Admitted", "value": status.get("Admitted", 0)},
		],
		"unsuccessful": status.get("Rejected", 0),
		"declined_or_lapsed": status.get("Declined", 0) + status.get("Lapsed", 0),
		"fee_unpaid": _count("Student Applicant", {**online_waiting, "educore_fee_status": "Unpaid"}),
		"offers_pending": _count("Student Applicant", {**base, "application_status": "Approved", "educore_offer_status": "Awaiting response"}),
		"total": len(applications),
		"offer_responses": _by("Student Applicant", "educore_offer_status", {**base, "educore_offer_status": ("is", "set")}),
		"by_month": _by_month([r.application_date for r in applications]),
		"by_programme": sorted(({"label": k, "value": v} for k, v in programmes.items()), key=lambda r: -r["value"])[:8],
		"by_pathway": sorted(({"label": k, "value": v} for k, v in pathway_counts.items()), key=lambda r: -r["value"]),
		"by_channel": [{"label": _("Online"), "value": online}, {"label": _("Paper"), "value": len(applications) - online}],
		"offerings": sorted(
			(o for o in offerings.values() if o["capacity"]), key=lambda o: -(o["taken"] / o["capacity"])
		)[:8],
	}


def _enrolment() -> dict:
	year = _intake_year()
	base = _in_scope({"academic_year": year} if year else {})
	return {
		"academic_year": year,
		"waiting": _count("Student Applicant", {**base, "application_status": "Approved"}),
		"enrolled": _count("Student Applicant", {**base, "application_status": "Admitted"}),
	}


def _registration() -> dict:
	from educore.registration import rules

	period = rules.current_period()
	if not period:
		return {"academic_year": None}
	base = _in_scope({"academic_year": period.academic_year, "educore_registration_status": ("is", "set")})
	return {
		"academic_year": period.academic_year,
		"state": rules.period_state(period),
		"closes_on": str(period.closes_on),
		"submitted": _count("Program Enrollment", {**base, "docstatus": 0, "educore_registration_status": "Submitted"}),
		"returned": _count("Program Enrollment", {**base, "docstatus": 0, "educore_registration_status": "Returned"}),
		"approved": _count("Program Enrollment", {**base, "docstatus": 1}),
	}


def _fees() -> dict:
	"""Student fees invoiced this calendar year, what is collected and what is owed, per campus"""
	year_start = f"{getdate(nowdate()).year}-01-01"
	rows = frappe.get_list(
		"Sales Invoice",
		filters=_in_scope({"docstatus": 1, "student": ("is", "set"), "posting_date": (">=", year_start)}),
		fields=["campus", {"SUM": "grand_total", "as": "invoiced"}, {"SUM": "outstanding_amount", "as": "outstanding"}],
		group_by="campus",
		limit=0,
	)
	campuses = [
		{"label": r.campus or "Not set", "invoiced": flt(r.invoiced, 2), "collected": flt(flt(r.invoiced) - flt(r.outstanding), 2)}
		for r in rows
	]
	invoiced = sum(c["invoiced"] for c in campuses)
	collected = sum(c["collected"] for c in campuses)
	return {
		"year": getdate(nowdate()).year,
		"invoiced": flt(invoiced, 2),
		"collected": flt(collected, 2),
		"outstanding": flt(invoiced - collected, 2),
		"by_campus": sorted(campuses, key=lambda c: -c["invoiced"]),
	}


# --- what is waiting for you ----------------------------------------------------------------------------


def _item(label: str, count: int, path: str, query: dict | None = None) -> dict | None:
	return {"label": label, "count": count, "to": {"path": path, **({"query": query} if query else {})}} if count else None


def _safely(build) -> list:
	"""One position's items; a queue this person may not read after all adds nothing"""
	try:
		return [i for i in build() if i]
	except (frappe.PermissionError, frappe.ValidationError):
		frappe.clear_messages()
		return []


def _work() -> list[dict]:
	"""What is waiting for the signed-in person, each with how many and where to act on it, in the order of the
	menu. Counts come from the queues themselves, so they follow the same campus and faculty scope."""
	items: list[dict] = []
	from educore.academics.lecturers import instructors_of

	if instructors_of(frappe.session.user):
		items += _safely(_lecturer_work)
	if _has(("Registrar", "Registry Officer", "System Manager")):
		items += _safely(_registry_work)
	if _has(("Faculty Officer", "Registrar")):
		items += _safely(_faculty_office_work)
	if _has(("Timetable Officer",)):
		items += _safely(_timetable_work)
	if _has(("Head of Department", "Dean")):
		items += _safely(_department_work)
	if _has(("Examinations Officer", "Registrar")):
		items += _safely(_examinations_work)
	if _has(("Bursar", "Finance Officer", "Student Fees Officer", "Cashier")):
		items += _safely(_finance_work)
	if _has(("HR Manager", "HR User")):
		items += _safely(_hr_work)
	if _has(("Student Affairs Officer", "Registrar")):
		items += _safely(_discipline_work)
	from educore.academics.service_requests import offices_of

	if offices_of():
		items += _safely(_service_work)
	seen, out = set(), []
	for i in items:
		key = (i["label"], i["to"]["path"])
		if key not in seen:
			seen.add(key)
			out.append(i)
	return out


def _my_groups(year: str | None = None) -> list[dict]:
	from educore.academics.lecturers import instructors_of

	instructors = instructors_of(frappe.session.user)
	if not instructors:
		return []
	names = frappe.get_all("Student Group Instructor", filters={"instructor": ("in", instructors), "parenttype": "Student Group"}, pluck="parent")
	groups = frappe.get_all("Student Group", filters={"name": ("in", names or [""]), "disabled": 0}, fields=["name", "course", "academic_year"])
	year = year or max((g.academic_year for g in groups), default=None)
	return [g for g in groups if g.academic_year == year]


def _lecturer_work() -> list:
	from frappe.utils import add_days, get_datetime, now_datetime

	from educore.academics import attendance
	from educore.academics.exam_timetable import duties_of

	groups = _my_groups()
	names = [g.name for g in groups]
	now = now_datetime()
	# lessons of the last week (today's once over) with no register yet
	missing = 0
	for g in names:
		for back in range(0, 7):
			day = add_days(nowdate(), -back)
			for lesson in attendance.lessons(g, day):
				if lesson["taken"] or get_datetime(f"{day} {lesson['end_time']}") > now:
					continue
				missing += 1
	sheets = {
		s.student_group: s
		for s in frappe.get_all(
			"Mark Sheet", filters={"student_group": ("in", names or [""])}, fields=["name", "student_group", "status", "plan_status", "plan_note", "return_note"]
		)
	}
	planned = set(frappe.get_all("Mark Sheet Assessment", filters={"parenttype": "Mark Sheet", "parent": ("in", [s.name for s in sheets.values()] or [""])}, pluck="parent", distinct=True))
	taught = [g for g in names if frappe.db.count("Student Group Student", {"parent": g, "active": 1})]
	open_ = [g for g in taught if (sheets.get(g) is None or sheets[g].status == "Draft")]
	to_set_up = sum(1 for g in open_ if not (sheets.get(g) and sheets[g].name in planned))
	returned = sum(1 for g in open_ if sheets.get(g) and not sheets[g].plan_status and sheets[g].plan_note and sheets[g].name in planned)
	marks_returned = sum(1 for g in open_ if sheets.get(g) and sheets[g].return_note)
	duties = sum(1 for d in duties_of(frappe.session.user) if str(d.get("exam_date")) >= nowdate())
	return [
		_item(_("Registers to take this week"), missing, "/attendance"),
		_item(_("Assessment plans returned to you"), returned, "/gradebook"),
		_item(_("Modules without an assessment plan"), to_set_up, "/gradebook"),
		_item(_("Marks returned to you"), marks_returned, "/marks"),
		_item(_("Invigilation duties ahead"), duties, "/my-timetable"),
	]


def _registry_work() -> list:
	from educore.api.v1 import studies_requests, transcripts

	return [
		_item(_("Studies requests to decide"), studies_requests.queue()["counts"]["Submitted"], "/studies-requests"),
		_item(_("Transcripts to issue"), transcripts.queue()["counts"]["Requested"], "/transcripts"),
	]


def _faculty_office_work() -> list:
	from educore.api.v1 import course_changes

	return [_item(_("Course changes to decide"), course_changes.queue()["counts"]["Submitted"], "/registrations", {"group": "senior", "status": "changes"})]


def _timetable_work() -> list:
	from educore.api.v1 import timetable

	unplaced = 0
	for campus in timetable.page()["campuses"]:
		unplaced += sum(1 for c in timetable.page(campus=campus)["classes"] if not c["hours"])
	return [_item(_("Classes without a time this semester"), unplaced, "/timetable")]


def _department_work() -> list:
	from educore.academics import workload
	from educore.api.v1 import academic_staff, examinations, teaching_allocation

	sheets = examinations.sheets()["rows"]
	plans = sum(1 for r in sheets if r["status"] == "Draft" and r["plan_status"] == "Proposed")
	moderate = sum(1 for r in sheets if r["status"] == "Submitted")
	no_lecturer = sum(1 for r in teaching_allocation.classes()["rows"] if r["state"] == "no-lecturer")
	load = academic_staff.workload()
	over = sum(1 for r in load["rows"] if r.get("status") == workload.OVER)
	return [
		_item(_("Assessment plans to approve"), plans, "/approvals"),
		_item(_("Marks to moderate"), moderate, "/approvals"),
		_item(_("Classes without a lecturer"), no_lecturer, "/teaching"),
		_item(_("Lecturers over the workload"), over, "/workload"),
	]


def _examinations_work() -> list:
	from educore.api.v1 import examinations

	rows = examinations.sheets()["rows"]
	return [
		_item(_("Marks to approve"), sum(1 for r in rows if r["status"] == "Moderated"), "/examinations", {"tab": "Moderated"}),
		_item(_("Results to publish"), sum(1 for r in rows if r["status"] == "Approved"), "/examinations", {"tab": "Approved"}),
		_item(_("Supplementary results to publish"), sum(1 for r in rows if r["supp_status"] == "Submitted"), "/examinations", {"tab": "supplementary"}),
	]


def _finance_work() -> list:
	from educore.api.v1 import student_payments, waivers

	items = [_item(_("Payments to assign"), len(student_payments._waiting()), "/student-payments")]
	if _has(("Bursar",)):
		waiting = sum(1 for w in waivers.waivers_list()["rows"] if w.get("status") == "Requested")
		items.append(_item(_("Fee waivers to decide"), waiting, "/waivers"))
	return items


def _hr_work() -> list:
	from educore.api.v1 import academic_staff

	rows = academic_staff.staff()["rows"]
	return [_item(_("Lecturers without an HR staff record"), sum(1 for r in rows if r["state"] != "Left" and "HR staff record" in r["missing"]), "/academic-staff", {"tab": "Incomplete"})]


def _lessons_today() -> list[dict]:
	"""The signed-in lecturer's lessons today, in order, each with its module and whether its register is taken"""
	from educore.academics import attendance

	out = []
	for g in _my_groups():
		code = frappe.db.get_value("Course", g.course, "educore_course_code")
		for lesson in attendance.lessons(g.name, nowdate()):
			out.append({**lesson, "group": g.name, "code": code or g.course, "course": frappe.db.get_value("Course", g.course, "course_name")})
	return sorted(out, key=lambda l: l["start_time"])


def _service_work() -> list:
	from educore.api.v1 import service_requests

	rows = [r for r in service_requests.queue()["rows"] if r["status"] in ("Submitted", "In progress")]
	return [
		_item(_("Service requests overdue"), sum(1 for r in rows if r["overdue"]), "/service-requests", {"tab": "overdue"}),
		_item(_("Service requests to answer"), len(rows), "/service-requests"),
	]


def _discipline_work() -> list:
	from educore.api.v1 import discipline

	rows = discipline.cases()["rows"]
	items = []
	if _has(("Student Affairs Officer",)):
		week_end = str(frappe.utils.add_days(nowdate(), 7))
		items += [
			_item(_("Misconduct reports to look into"), sum(1 for r in rows if r["status"] == "Reported"), "/discipline"),
			_item(_("Disciplinary hearings this week"), sum(1 for r in rows if r["status"] == "Hearing" and r["hearing_on"] and r["hearing_on"][:10] <= week_end), "/discipline", {"tab": "Hearing"}),
		]
	if _has(("Registrar",)):
		items.append(_item(_("Disciplinary appeals to decide"), sum(1 for r in rows if r["status"] == "Appealed"), "/discipline", {"tab": "Appealed"}))
	return items
