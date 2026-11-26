"""Official transcripts: a student's request, the fee, and the Registry issuing it.

A student (also one who has completed or left) asks for an official transcript on My studies: how many copies, and
collected at the campus, emailed to an institution or employer, or posted. When the university charges for
transcripts (Registration Settings, transcript_fee per copy, set by the Bursar), the request is invoiced at once to
the student, and paid like any fee (by EFT with the student number). The Registry issues it once the fee is paid and,
where the university requires it (transcript_needs_clearance), the student is financially cleared:

- emailed: the academic record PDF (educore.api.v1.documents) goes to the address given, from the Registry;
- collected or posted: the Registry prints it, stamps and signs it, and records it as issued.

The transcript is the academic record itself: only published results, with its verification code. The student is
emailed when it is issued or declined (educore.academics.notify).
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate, validate_email_address

COLLECT, EMAIL, POST = "Collect at the campus", "Email", "Post"
DELIVERIES = (COLLECT, EMAIL, POST)
REQUESTED, ISSUED, DECLINED = "Requested", "Issued", "Declined"
FEE_ITEM = "Transcript Fee"
MAX_COPIES = 10


def settings():
	rules = frappe.get_cached_doc("Registration Settings")
	return frappe._dict(fee=flt(rules.get("transcript_fee")), needs_clearance=bool(rules.get("transcript_needs_clearance")))


def request(student: str, copies: int, delivery: str, recipient: str | None = None, email: str | None = None, postal_address: str | None = None) -> str:
	copies = cint(copies)
	if not 1 <= copies <= MAX_COPIES:
		frappe.throw(_("Ask for 1 to {0} copies").format(MAX_COPIES))
	if delivery not in DELIVERIES:
		frappe.throw(_("Choose how you receive the transcript"))
	recipient = (recipient or "").strip()
	email = (email or "").strip()
	postal_address = (postal_address or "").strip()
	if delivery == EMAIL:
		if not email or not validate_email_address(email):
			frappe.throw(_("Enter the email address to send it to"))
		if not recipient:
			frappe.throw(_("Say who it is for"))
		copies = 1  # one emailed copy; the recipient verifies it with the university
	if delivery == POST and (not postal_address or not recipient):
		frappe.throw(_("Enter who it is for and the postal address"))
	if delivery == EMAIL and frappe.db.exists("Transcript Request", {"student": student, "status": REQUESTED, "email": email}):
		frappe.throw(_("A transcript to {0} is waiting already").format(email))

	fee = flt(settings().fee * copies, 2)
	doc = frappe.get_doc(
		{
			"doctype": "Transcript Request",
			"student": student,
			"copies": copies,
			"delivery": delivery,
			"recipient": recipient or None,
			"email": email if delivery == EMAIL else None,
			"postal_address": postal_address if delivery == POST else None,
			"status": REQUESTED,
			"fee": fee,
			"requested_by": frappe.session.user,
			"requested_on": nowdate(),
		}
	).insert(ignore_permissions=True)
	if fee:
		doc.db_set("fee_invoice", _invoice(doc))
	return doc.name


def _invoice(doc) -> str:
	"""The transcript fee, invoiced to the student and posted to their campus"""
	from education.education.doctype.fee_schedule.fee_schedule import get_customer_from_student

	from educore.finance.student_fees import _as_system, ensure_fee_setup, ensure_fiscal_year

	with _as_system():
		company = frappe.db.get_value("Campus", doc.campus, "company") or frappe.defaults.get_global_default("company")
		if not frappe.db.exists("Item", FEE_ITEM):
			ensure_fee_setup(company)
		cost_center = frappe.db.get_value("Campus", doc.campus, "cost_center") or frappe.get_cached_value("Company", company, "cost_center")
		ensure_fiscal_year(nowdate(), company)
		invoice = frappe.new_doc("Sales Invoice")
		invoice.update(
			{
				"customer": get_customer_from_student(doc.student),
				"student": doc.student,
				"company": company,
				"set_posting_time": 1,
				"posting_date": nowdate(),
				"due_date": nowdate(),
				"cost_center": cost_center,
				"campus": doc.campus,
				"remarks": _("Official transcript, {0} ({1})").format(doc.name, doc.delivery),
			}
		)
		invoice.append(
			"items",
			{
				"item_code": FEE_ITEM,
				"item_name": FEE_ITEM,
				"description": _("Official transcript, {0} copies").format(doc.copies) if doc.copies > 1 else _("Official transcript"),
				"qty": doc.copies,
				"rate": settings().fee,
				"cost_center": cost_center,
				"income_account": frappe.db.get_value("Fee Category Default", {"parent": FEE_ITEM, "company": company}, "income_account"),
			},
		)
		invoice.insert(ignore_permissions=True)
		invoice.submit()
		return invoice.name


def blockers(doc) -> list[str]:
	"""What stops the Registry issuing it now, in plain words (empty: nothing)"""
	found = []
	if doc.fee_invoice and flt(frappe.db.get_value("Sales Invoice", doc.fee_invoice, "outstanding_amount")) > 0:
		found.append(_("Transcript fee not paid"))
	if settings().needs_clearance:
		from educore.finance import clearance

		state = clearance.status(doc.student, leave_out=doc.fee_invoice)
		if not state["cleared"]:
			found += [r for r in state["reasons"] if r]
	return found


def issue(name: str) -> "frappe.model.document.Document":
	from educore.academics import notify

	doc = frappe.get_doc("Transcript Request", name)
	if doc.status != REQUESTED:
		frappe.throw(_("This request is {0} already").format(doc.status.lower()))
	stopping = blockers(doc)
	if stopping:
		frappe.throw(_("Not issued: {0}").format("; ".join(stopping)))
	if doc.delivery == EMAIL:
		_email(doc)
	doc.db_set({"status": ISSUED, "issued_by": frappe.session.user, "issued_on": nowdate()})
	how = {
		COLLECT: _("It is ready to collect at the Registry on your campus."),
		EMAIL: _("It was emailed to {0} at {1}.").format(doc.recipient, doc.email),
		POST: _("It was posted to {0}.").format(doc.recipient),
	}[doc.delivery]
	notify.send(doc.student, "transcript_issued", doc, how=how)
	return doc


def _email(doc):
	"""The academic record PDF to the address the student gave, from the Registry"""
	from educore.admissions.notify import can_send, university
	from educore.api.v1.documents import academic_record_pdf

	if not can_send():
		frappe.throw(_("No outgoing email account is set up: print the transcript and post it instead, or set up email first"))
	student_name = frappe.db.get_value("Student", doc.student, "student_name")
	body = (
		f"<p>{_('Dear {0},').format(frappe.utils.escape_html(doc.recipient))}</p>"
		f"<p>{_('At the request of {0} (student number {1}), the official transcript of their studies is attached.').format(frappe.utils.escape_html(student_name), doc.student)}</p>"
		f"<p>{_('Its code at the foot of the page confirms it with the university.')}</p>"
		f"<p>{_('Office of the Registrar')}<br>{frappe.utils.escape_html(university())}</p>"
	)
	frappe.sendmail(
		recipients=[doc.email],
		subject=_("Official transcript: {0}").format(student_name),
		message=body,
		attachments=[{"fname": f"Transcript {doc.student}.pdf", "fcontent": academic_record_pdf(doc.student)}],
		reference_doctype=doc.doctype,
		reference_name=doc.name,
	)


def decline(name: str, note: str) -> "frappe.model.document.Document":
	"""Not issued, with the reason; an unpaid fee invoice is cancelled (a fee already paid is Finance's to refund)"""
	from educore.academics import notify
	from educore.finance.student_fees import _as_system

	if not (note or "").strip():
		frappe.throw(_("Tell the student why"))
	doc = frappe.get_doc("Transcript Request", name)
	if doc.status != REQUESTED:
		frappe.throw(_("This request is {0} already").format(doc.status.lower()))
	if doc.fee_invoice:
		total, outstanding = frappe.db.get_value("Sales Invoice", doc.fee_invoice, ["grand_total", "outstanding_amount"])
		if flt(outstanding) >= flt(total):
			with _as_system():
				frappe.get_doc("Sales Invoice", doc.fee_invoice).cancel()
	doc.db_set({"status": DECLINED, "issued_by": frappe.session.user, "issued_on": nowdate(), "review_note": note.strip()})
	notify.send(doc.student, "transcript_declined", doc, note=doc.review_note)
	return doc
