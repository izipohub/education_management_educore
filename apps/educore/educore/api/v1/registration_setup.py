"""Registration setup, for the Registrar: when each year's registration opens and closes and late registration
ends (Registration Period), and the academic rules (Registration Settings: credit limit, faculty approval). The
money (outstanding balance allowed, deposit, late fee) is Finance's, set in educore.api.v1.fee_settings and shown
here read only. Only the fields listed here can be changed; saving is recorded as the signed-in user.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from educore.registration import rules

SETUP_ROLES = ("Registrar", "System Manager")
SETTINGS_FIELDS = ("max_outstanding", "deposit_type", "deposit_value", "max_credits", "approval_needed")
DEPOSIT_TYPES = ("None", "Amount", "Percent of the year's fees")
#: shown on the Registrar's screen, set by Finance
FINANCE_FIELDS = ("max_outstanding", "deposit_type", "deposit_value")


def _require_role():
	if not set(frappe.get_roles()) & set(SETUP_ROLES):
		frappe.throw(_("Only the Registrar sets up registration"), frappe.PermissionError)


def _period(doc) -> dict:
	return {
		"name": doc.name,
		"academic_year": doc.academic_year,
		"opens_on": str(doc.opens_on) if doc.opens_on else None,
		"closes_on": str(doc.closes_on) if doc.closes_on else None,
		"late_until": str(doc.late_until) if doc.late_until else None,
		"late_fee": flt(doc.late_fee),
		"state": rules.period_state(doc) if doc.opens_on and doc.closes_on else None,
		"registrations": frappe.db.count(
			"Program Enrollment", {"academic_year": doc.academic_year, "educore_registration_status": ("is", "set")}
		),
	}


@frappe.whitelist(methods=["GET"])
def setup() -> dict:
	_require_role()
	settings = rules.settings()
	periods = [frappe.get_doc("Registration Period", name) for name in frappe.get_all("Registration Period", pluck="name")]
	periods.sort(key=lambda p: str(p.academic_year), reverse=True)
	taken = {p.academic_year for p in periods}
	return {
		"settings": {field: settings.get(field) for field in SETTINGS_FIELDS},
		"periods": [_period(p) for p in periods],
		"academic_years": [y for y in frappe.get_all("Academic Year", pluck="name", order_by="name desc") if y not in taken],
		"deposit_types": list(DEPOSIT_TYPES),
	}


@frappe.whitelist(methods=["POST"])
def save_settings(data: dict | str) -> dict:
	_require_role()
	data = frappe.parse_json(data)
	settings = frappe.get_single("Registration Settings")
	# the balance allowed and the deposit are Finance's (educore.api.v1.fee_settings): shown here, changed there
	for field in FINANCE_FIELDS:
		before, after = settings.get(field), data.get(field)
		changed = (after != before) if field == "deposit_type" else (flt(after, 2) != flt(before, 2))
		if field in data and changed:
			frappe.throw(_("{0} is set by Finance").format(frappe.get_meta("Registration Settings").get_label(field)), frappe.PermissionError)
	if "max_credits" in data:
		settings.max_credits = cint(data["max_credits"])
		if not 0 <= settings.max_credits <= 400:
			frappe.throw(_("Most credits per year must be between 0 (no limit) and 400"))
	if "approval_needed" in data:
		settings.approval_needed = 1 if data["approval_needed"] in (True, 1, "1", "true") else 0
	settings.save(ignore_permissions=True)
	return setup()


@frappe.whitelist(methods=["POST"])
def save_period(data: dict | str, name: str | None = None) -> dict:
	"""A year's registration period: new (name empty) or changed"""
	_require_role()
	data = frappe.parse_json(data)
	if name:
		doc = frappe.get_doc("Registration Period", name)
	else:
		year = data.get("academic_year")
		if not year or not frappe.db.exists("Academic Year", year):
			frappe.throw(_("Choose the academic year"))
		if frappe.db.exists("Registration Period", {"academic_year": year}):
			frappe.throw(_("{0} already has a registration period").format(year))
		doc = frappe.new_doc("Registration Period")
		doc.academic_year = year
	for field in ("opens_on", "closes_on", "late_until"):
		if field in data:
			doc.set(field, data[field] or None)
	# the late fee is Finance's (educore.api.v1.fee_settings): shown here, changed there
	if "late_fee" in data and flt(data["late_fee"], 2) != flt(doc.late_fee, 2):
		frappe.throw(_("The late registration fee is set by Finance"), frappe.PermissionError)
	if not doc.opens_on or not doc.closes_on:
		frappe.throw(_("Give the dates registration opens and closes"))
	if getdate(doc.closes_on) < getdate(doc.opens_on):
		frappe.throw(_("Registration closes before it opens"))
	if doc.late_until and getdate(doc.late_until) < getdate(doc.closes_on):
		frappe.throw(_("Late registration ends before registration closes"))
	if doc.late_fee < 0:
		frappe.throw(_("The late fee cannot be negative"))
	doc.flags.ignore_permissions = True
	doc.save()
	return setup()
