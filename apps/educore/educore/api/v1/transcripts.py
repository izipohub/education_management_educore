"""Official transcripts: the student asks on My studies; the Registry issues or declines (educore.academics.transcripts).
Registry staff see their campus's requests."""

import frappe
from frappe import _
from frappe.utils import flt

from educore.academics import transcripts
from educore.api.v1.registration import _student

#: who issues transcripts
ISSUE_ROLES = ("Registrar", "Registry Officer", "System Manager")
STATUSES = (transcripts.REQUESTED, transcripts.ISSUED, transcripts.DECLINED)
FIELDS = [
	"name", "student", "student_name", "campus", "copies", "delivery", "recipient", "email", "postal_address", "status",
	"fee", "fee_invoice", "requested_on", "issued_on", "review_note",
]


def _row(r, with_blockers: bool = False) -> dict:
	paid = not r.fee_invoice or flt(frappe.db.get_value("Sales Invoice", r.fee_invoice, "outstanding_amount")) <= 0
	row = {
		**r,
		"requested_on": str(r.requested_on) if r.requested_on else None,
		"issued_on": str(r.issued_on) if r.issued_on else None,
		"paid": paid,
	}
	if with_blockers and r.status == transcripts.REQUESTED:
		row["blockers"] = transcripts.blockers(r)
	return row


# --- the student ---------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def mine() -> dict:
	student = _student()
	rules = transcripts.settings()
	return {
		"requests": [
			_row(r)
			for r in frappe.get_all("Transcript Request", filters={"student": student}, fields=FIELDS, order_by="creation desc")
		],
		"fee": rules.fee,
		"needs_clearance": rules.needs_clearance,
		"deliveries": transcripts.DELIVERIES,
		"has_results": bool(
			frappe.db.sql(
				"""select 1 from `tabMark Sheet Entry` e join `tabMark Sheet` ms on ms.name = e.parent
				where ms.status = 'Published' and e.student = %s limit 1""",
				student,
			)
		),
	}


@frappe.whitelist(methods=["POST"])
def request(copies: int, delivery: str, recipient: str | None = None, email: str | None = None, postal_address: str | None = None) -> dict:
	student = _student()
	transcripts.request(student, copies, delivery, recipient, email, postal_address)
	return mine()


# --- the Registry --------------------------------------------------------------------------------------


def _require():
	if not set(frappe.get_roles()) & set(ISSUE_ROLES):
		frappe.throw(_("Transcripts are issued by the Registry"), frappe.PermissionError)


def _scoped(name: str):
	from educore.access.scope import campuses

	_require()
	campus = frappe.db.get_value("Transcript Request", name, "campus")
	if campus is None and not frappe.db.exists("Transcript Request", name):
		frappe.throw(_("Unknown request {0}").format(name))
	if campus not in campuses():
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def queue(status: str = transcripts.REQUESTED) -> dict:
	from educore.access.scope import campuses

	_require()
	if status not in STATUSES:
		frappe.throw(_("Unknown status {0}").format(status))
	scope = list(campuses()) or [""]
	counts = {s: frappe.db.count("Transcript Request", {"status": s, "campus": ("in", scope)}) for s in STATUSES}
	rows = frappe.get_all(
		"Transcript Request",
		filters={"status": status, "campus": ("in", scope)},
		fields=FIELDS,
		order_by="requested_on asc, creation asc" if status == transcripts.REQUESTED else "issued_on desc, creation desc",
		limit=200,
	)
	return {"rows": [_row(r, with_blockers=True) for r in rows], "counts": counts}


@frappe.whitelist(methods=["POST"])
def issue(name: str) -> dict:
	_scoped(name)
	transcripts.issue(name)
	return queue()


@frappe.whitelist(methods=["POST"])
def decline(name: str, note: str) -> dict:
	_scoped(name)
	transcripts.decline(name, note)
	return queue()
