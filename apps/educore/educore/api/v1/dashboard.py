"""The staff home: the numbers each position needs, for the campuses and faculties the user works on.

Every figure comes through frappe.get_list (or get_all only after a permission check), so campus and faculty
User Permissions apply: an Oshakati officer's dashboard counts Oshakati only. A section appears only for the roles
it concerns, and only when the user may read what it counts.
"""

import frappe
from frappe.utils import flt, getdate, nowdate

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


@frappe.whitelist(methods=["GET"])
def stats() -> dict:
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
	return {"today": nowdate(), "sections": sections}


def _students() -> dict:
	filters = {"enabled": 1}
	return {"total": _count("Student", filters), "by_campus": _by("Student", "campus", filters)}


def _admissions() -> dict:
	year = _intake_year()
	base = {"academic_year": year} if year else {}
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
		"offerings": sorted(
			(o for o in offerings.values() if o["capacity"]), key=lambda o: -(o["taken"] / o["capacity"])
		)[:8],
	}


def _enrolment() -> dict:
	year = _intake_year()
	base = {"academic_year": year} if year else {}
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
	base = {"academic_year": period.academic_year, "educore_registration_status": ("is", "set")}
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
		filters={"docstatus": 1, "student": ("is", "set"), "posting_date": (">=", year_start)},
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
