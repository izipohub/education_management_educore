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
	if frappe.has_permission("Student", "read"):
		sections["students"] = _students()
	if _has(ADMISSIONS) and frappe.has_permission("Student Applicant", "read"):
		sections["admissions"] = _admissions()
	if _has(ENROLMENT) and frappe.has_permission("Student Applicant", "read"):
		sections["enrolment"] = _enrolment()
	if _has(REGISTRATION) and frappe.has_permission("Program Enrollment", "read"):
		sections["registration"] = _registration()
	if _has(FEES) and frappe.has_permission("Sales Invoice", "read"):
		sections["fees"] = _fees()
	return {"today": nowdate(), "campus": campus, "campuses": campuses, "sections": sections}


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
