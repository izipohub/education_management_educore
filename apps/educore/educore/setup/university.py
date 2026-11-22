"""Sets a new site up as one university, without clicking through the setup wizard.

    bench --site <site> execute educore.setup.university.setup_university --kwargs "{
        'company_name': 'University of …', 'abbr': 'UOX',
        'fy_start_date': '2026-01-01', 'fy_end_date': '2026-12-31'}"

It runs the same setup as the desk wizard (Frappe, ERPNext and HRMS stages: country defaults, the Company,
its chart of accounts and financial year), with Namibian defaults (AGENT.md 9), then EduCore's own steps:

- ERPNext's default cost center "Main" becomes "Central Administration", for shared university costs;
  each campus gets its own cost center when it is created (Campus, AGENT.md 5.1.2).
- ERPNext's trading-company departments (Sales, Marketing, Dispatch, …) are removed while nothing links
  to them; the university's own units are added as Faculties, Schools and Divisions.

Running it again on a site that is already set up changes nothing.
"""

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

NAMIBIA = {
	"country": "Namibia",
	"currency": "NAD",
	"timezone": "Africa/Windhoek",
	"language": "English",
}

#: Departments ERPNext creates for every new company; a university has no use for them
ERPNEXT_DEFAULT_DEPARTMENTS = (
	"Accounts",
	"Marketing",
	"Sales",
	"Purchase",
	"Operations",
	"Production",
	"Dispatch",
	"Customer Service",
	"Human Resources",
	"Management",
	"Quality Management",
	"Research & Development",
	"Legal",
)

CENTRAL_COST_CENTER = "Central Administration"


def setup_university(
	company_name: str,
	abbr: str,
	fy_start_date: str,
	fy_end_date: str,
	country: str | None = None,
	currency: str | None = None,
	timezone: str | None = None,
) -> str:
	if not frappe.is_setup_complete():
		args = {
			**NAMIBIA,
			"company_name": company_name,
			"company_abbr": abbr,
			"chart_of_accounts": "Standard",
			"fy_start_date": fy_start_date,
			"fy_end_date": fy_end_date,
		}
		for key, value in (("country", country), ("currency", currency), ("timezone", timezone)):
			if value:
				args[key] = value
		# bench new-site can leave Frappe's own stage marked done with no region saved; the wizard then
		# skips that stage and hands the other apps an empty country. On a site that never finished setup,
		# run every stage.
		if not frappe.db.get_single_value("System Settings", "country"):
			frappe.db.set_value("Installed Application", {"app_name": "frappe"}, "is_setup_complete", 0)
			# the wizard reads that flag through the client cache
			frappe.clear_cache()
		result = setup_complete(args)
		if not frappe.is_setup_complete():
			frappe.throw(f"University setup failed: {result}")

	company = frappe.db.get_value("Company", {"company_name": company_name}) or company_name
	allow_registration_day_user_volume()
	rename_main_cost_center(company)
	remove_default_departments(company)

	from educore.finance.student_fees import ensure_fee_setup

	ensure_fee_setup(company)
	frappe.db.commit()
	return company


#: New logins per hour. Frappe's default (60) guards a public sign-up form; a registry office enrolling an
#: intake creates a student login per enrolment and would be stopped mid-morning on registration day.
USERS_PER_HOUR = 1000


def allow_registration_day_user_volume():
	"""Raise Frappe's new-user throttle to a university's volume, unless the site already sets its own"""
	from frappe.installer import update_site_config

	if not frappe.conf.get("throttle_user_limit"):
		update_site_config("throttle_user_limit", USERS_PER_HOUR)
		frappe.local.conf["throttle_user_limit"] = USERS_PER_HOUR


def rename_main_cost_center(company: str):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	main, central = f"Main - {abbr}", f"{CENTRAL_COST_CENTER} - {abbr}"
	if frappe.db.exists("Cost Center", main) and not frappe.db.exists("Cost Center", central):
		frappe.rename_doc("Cost Center", main, central, force=True)
		frappe.db.set_value("Cost Center", central, "cost_center_name", CENTRAL_COST_CENTER)


def remove_default_departments(company: str):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	for name in ERPNEXT_DEFAULT_DEPARTMENTS:
		department = f"{name} - {abbr}"
		if not frappe.db.exists("Department", department):
			continue
		if frappe.db.get_value("Department", department, "educore_unit_type"):
			continue
		try:
			frappe.delete_doc("Department", department, ignore_permissions=True)
		except frappe.LinkExistsError:
			# something already uses it: keep it
			pass
