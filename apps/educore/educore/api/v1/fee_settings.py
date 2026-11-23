"""Fee settings, for Finance: what applicants and students pay, and where it is booked.

The amounts and accounts are Finance's (the fees booklet), not the Registrar's: the application fees (online and
paper, local and international) and the ERPNext bank and income accounts (Admission Settings); the outstanding
balance allowed and the deposit before registering (Registration Settings); and each year's late registration fee
(Registration Period, whose dates the Registrar sets). The Bursar changes them; finance officers read them.
"""

import frappe
from frappe import _
from frappe.utils import flt

from educore.api.v1 import admission_setup, registration_setup

#: who changes the fees and accounts
EDIT_ROLES = ("Bursar", "System Manager")
#: who reads them
READ_ROLES = (*EDIT_ROLES, "Finance Officer", "Student Fees Officer")

APPLICATION_FIELDS = ("fee_namibian", "fee_international", "fee_paper_local", "fee_paper_international", "fee_bank_account", "fee_income_account")
REGISTRATION_FIELDS = ("max_outstanding", "deposit_type", "deposit_value")


def can_edit() -> bool:
	return bool(set(frappe.get_roles()) & set(EDIT_ROLES))


def _require(roles):
	if not set(frappe.get_roles()) & set(roles):
		frappe.throw(_("Fee settings are Finance's"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def settings() -> dict:
	_require(READ_ROLES)
	admission = frappe.get_single("Admission Settings")
	registration = frappe.get_single("Registration Settings")
	periods = [frappe.get_doc("Registration Period", n) for n in frappe.get_all("Registration Period", pluck="name")]
	periods.sort(key=lambda p: str(p.academic_year), reverse=True)
	return {
		"application": {f: admission.get(f) for f in APPLICATION_FIELDS},
		"registration": {f: registration.get(f) for f in REGISTRATION_FIELDS},
		"late_fees": [
			{"name": p.name, "academic_year": p.academic_year, "late_until": str(p.late_until) if p.late_until else None, "late_fee": flt(p.late_fee)}
			for p in periods
		],
		"bank_accounts": admission_setup._bank_accounts(),
		"income_accounts": frappe.get_all(
			"Account", filters={"root_type": "Income", "is_group": 0, "disabled": 0}, pluck="name", order_by="name asc"
		),
		"deposit_types": list(registration_setup.DEPOSIT_TYPES),
		"can_edit": can_edit(),
	}


@frappe.whitelist(methods=["POST"])
def save(data: dict | str) -> dict:
	"""Any of the application fees and accounts, the registration deposit and balance, and late fees per period"""
	_require(EDIT_ROLES)
	data = frappe.parse_json(data)

	application = data.get("application") or {}
	if application:
		doc = frappe.get_single("Admission Settings")
		for field in APPLICATION_FIELDS:
			if field in application:
				doc.set(field, admission_setup._clean(field, admission_setup.SETTINGS_FIELDS[field], application[field]))
		doc.save(ignore_permissions=True)

	registration = data.get("registration") or {}
	if registration:
		doc = frappe.get_single("Registration Settings")
		if "max_outstanding" in registration:
			doc.max_outstanding = flt(registration["max_outstanding"], 2)
			if doc.max_outstanding < 0:
				frappe.throw(_("The outstanding balance allowed cannot be negative"))
		if "deposit_type" in registration:
			if registration["deposit_type"] not in registration_setup.DEPOSIT_TYPES:
				frappe.throw(_("Choose how the deposit is set"))
			doc.deposit_type = registration["deposit_type"]
		if "deposit_value" in registration:
			doc.deposit_value = flt(registration["deposit_value"], 2)
		if doc.deposit_value < 0 or (doc.deposit_type == "Percent of the year's fees" and doc.deposit_value > 100):
			frappe.throw(_("The deposit must be between 0 and 100 percent of the year's fees"))
		doc.save(ignore_permissions=True)

	for row in data.get("late_fees") or []:
		period = frappe.get_doc("Registration Period", row.get("name"))
		period.late_fee = flt(row.get("late_fee"), 2)
		if period.late_fee < 0:
			frappe.throw(_("The late fee cannot be negative"))
		period.save(ignore_permissions=True)
	return settings()
