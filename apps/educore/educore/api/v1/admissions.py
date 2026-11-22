"""Admission decisions, for the Vue app's admissions queue.

Reads go through frappe.get_list, so each officer sees only the applicants their campus User Permission
allows. Decisions go through the "EduCore Admission Decision" workflow, which checks the role, and the
applicant's validation, which checks intake capacity and the reason (educore.academics.students).
"""

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow, get_transitions

STATUSES = ("Applied", "Approved", "Rejected", "Admitted")
NEEDS_REASON = ("Reject", "Withdraw Offer")

FIELDS = [
	"name",
	"title",
	"first_name",
	"last_name",
	"educore_programme_offering as offering",
	"program",
	"campus",
	"educore_mode_of_study as mode_of_study",
	"academic_year",
	"application_date",
	"application_status as status",
	"educore_decided_by as decided_by",
	"educore_decided_on as decided_on",
	"educore_decision_reason as decision_reason",
]


def _actions(name: str) -> list[str]:
	"""The workflow actions the current user may take on this applicant now"""
	doc = frappe.get_doc("Student Applicant", name)
	if not doc.has_permission("write"):
		return []
	return [t.action for t in get_transitions(doc)]


def _row(row) -> dict:
	row = dict(row)
	row["applicant"] = row.get("title") or " ".join(p for p in (row.get("first_name"), row.get("last_name")) if p)
	row["actions"] = _actions(row["name"])
	return row


def _filters(status: str, academic_year: str | None) -> dict:
	filters = {"application_status": status}
	if academic_year:
		filters["academic_year"] = academic_year
	return filters


@frappe.whitelist(methods=["GET"])
def applications(
	status: str = "Applied",
	academic_year: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	if status not in STATUSES:
		frappe.throw(_("Unknown status {0}").format(status))
	years = sorted(
		set(frappe.get_list("Student Applicant", pluck="academic_year", distinct=True, limit=0)), reverse=True
	)
	# no year asked for: the newest year this user has applications in
	academic_year = academic_year or (years[0] if years else None)
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [["first_name", "like", like], ["last_name", "like", like], ["name", "like", like]]

	rows = frappe.get_list(
		"Student Applicant",
		filters=_filters(status, academic_year),
		or_filters=or_filters,
		fields=FIELDS,
		order_by="application_date asc, name asc",
		start=int(start),
		page_length=min(int(page_length), 200),
	)
	counts = {
		s: len(frappe.get_list("Student Applicant", filters=_filters(s, academic_year), pluck="name", limit=0))
		for s in STATUSES
	}
	return {
		"rows": [_row(r) for r in rows],
		"counts": counts,
		"academic_year": academic_year,
		"academic_years": years,
		"capacity": _capacity({r.offering for r in rows if r.offering}, {r.academic_year for r in rows}),
	}


def _capacity(offerings: set[str], years: set[str]) -> dict:
	"""Places offered so far against each offering's intake capacity, per academic year"""
	result = {}
	for offering in offerings:
		capacity = frappe.db.get_value("Programme Offering", offering, "intake_capacity") or None
		for year in years:
			taken = frappe.db.count(
				"Student Applicant",
				{
					"educore_programme_offering": offering,
					"academic_year": year,
					"application_status": ("in", ("Approved", "Admitted")),
				},
			)
			result[f"{offering}|{year}"] = {"capacity": capacity, "taken": taken}
	return result


@frappe.whitelist(methods=["POST"])
def decide(name: str, action: str, reason: str | None = None) -> dict:
	"""Approve, Reject, Withdraw Offer or Reconsider an application"""
	doc = frappe.get_doc("Student Applicant", name)
	# campus scope and role: before anything is written
	doc.check_permission("write")
	if action in NEEDS_REASON:
		if not (reason or "").strip():
			frappe.throw(_("Give the reason for this decision"))
		# saved first: the workflow action reloads the applicant from the database
		doc.db_set("educore_decision_reason", reason.strip())
	apply_workflow(doc, action)
	row = frappe.get_list("Student Applicant", filters={"name": name}, fields=FIELDS, limit=1)[0]
	return _row(row)
