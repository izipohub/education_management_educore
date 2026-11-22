"""Emails to applicants about their online application.

Sent when Admission Settings say so (notify_applicants), to the applicant's login email, queued through Frappe's
Email Queue with the application as the reference (so each email also appears on its timeline). Paper
applications captured by staff have no applicant login and get none.
"""

import frappe
from frappe import _
from frappe.utils import escape_html, formatdate, get_url

#: event: (subject, paragraphs); {placeholders} are filled from _context()
TEMPLATES = {
	"submitted": (
		"Application {name} received",
		[
			"Dear {first_name},",
			"Thank you for applying to {university}. We have received your application {name} for the {intake}.",
			"The Admissions Office will now verify your documents and assess your application. You can follow its "
			"progress in the applicant portal.",
			"{fee_paragraph}",
		],
	),
	"document_rejected": (
		"Action required: {document} for application {name}",
		[
			"Dear {first_name},",
			"The Admissions Office could not accept the document {document} for the following reason: {reason}",
			"Please upload a new certified copy in the applicant portal. Your application cannot be decided until this "
			"document is verified.",
		],
	),
	"offer_made": (
		"Offer of a place: {programme}",
		[
			"Dear {first_name},",
			"We are pleased to offer you a place in the {programme} at {campus} ({mode}), for the {intake}.",
			"{conditions_paragraph}",
			"Please accept or decline this offer in the applicant portal by {deadline}. If we have not received your "
			"response by then, the offer will lapse and the place will be offered to another applicant.",
		],
	),
	"offer_reminder": (
		"Reminder: please respond to your offer by {deadline}",
		[
			"Dear {first_name},",
			"Your offer of a place in the {programme} at {campus} is awaiting your response.",
			"Please accept or decline it in the applicant portal by {deadline}, after which it will lapse.",
		],
	),
	"offer_accepted": (
		"Offer accepted: {programme}",
		[
			"Dear {first_name},",
			"Thank you for accepting your place in the {programme} at {campus}.",
			"The Registry will contact you about registration before the start of the academic year.",
		],
	),
	"offer_declined": (
		"Offer declined: {programme}",
		[
			"Dear {first_name},",
			"We confirm that you have declined the offer of a place in the {programme} at {campus}.",
			"Should you wish to reconsider, please contact the Admissions Office.",
		],
	),
	"offer_lapsed": (
		"Offer lapsed: {programme}",
		[
			"Dear {first_name},",
			"The offer of a place in the {programme} at {campus} has lapsed, as no response was received by {deadline}.",
			"Should you wish to discuss this, please contact the Admissions Office.",
		],
	),
	"unsuccessful": (
		"Outcome of application {name}",
		[
			"Dear {first_name},",
			"Thank you for your application to {university}. After careful consideration, we regret that we are unable "
			"to offer you a place for the {intake}.",
			"{reason_paragraph}",
		],
	),
}


def enabled() -> bool:
	return bool(frappe.get_cached_doc("Admission Settings").notify_applicants)


def university() -> str:
	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
	return company or frappe.db.get_default("company") or "the university"


def portal_url() -> str:
	base = frappe.conf.get("educore_app_url") or get_url()
	return f"{base.rstrip('/')}/application"


def _context(doc, extra: dict) -> dict:
	offering = (
		frappe.db.get_value("Programme Offering", doc.educore_programme_offering, ["campus", "mode_of_study"], as_dict=True)
		if doc.get("educore_programme_offering")
		else None
	)
	reason = doc.get("educore_decision_reason")
	conditions = doc.get("educore_offer_conditions")
	fee = doc.get("educore_fee_amount")
	context = {
		"name": doc.name,
		"first_name": doc.first_name or doc.title,
		"university": university(),
		"intake": doc.student_admission or doc.academic_year,
		"programme": doc.program or "",
		"campus": offering.campus if offering else (doc.get("campus") or ""),
		"mode": (offering.mode_of_study if offering else "").lower(),
		"deadline": formatdate(doc.educore_offer_deadline) if doc.get("educore_offer_deadline") else "",
		"conditions_paragraph": _("This offer is subject to the following conditions: {0}").format(conditions) if conditions else "",
		"reason_paragraph": _("Reason: {0}").format(reason) if reason else "",
		"fee_paragraph": (
			_("If you have not yet paid the application fee of N$ {0}, please pay it with {1} as the payment reference.").format(
				frappe.utils.fmt_money(fee, precision=2), doc.name
			)
			if fee and doc.get("educore_fee_status") == "Unpaid"
			else ""
		),
	}
	context.update(extra)
	return context


def render(event: str, doc, **extra) -> tuple[str, str]:
	subject, paragraphs = TEMPLATES[event]
	context = {key: escape_html(str(value)) if isinstance(value, str) else value for key, value in _context(doc, extra).items()}
	body = "".join(f"<p>{_(p).format(**context)}</p>" for p in paragraphs if _(p).format(**context))
	link = portal_url()
	body += f'<p><a href="{link}">{_("Open the applicant portal")}</a></p>'
	body += f"<p>{_('Admissions Office')}<br>{escape_html(university())}</p>"
	return _(subject).format(**_context(doc, extra)), body


def send(doc, event: str, **extra):
	"""Queue the email for this event, if the university emails applicants and this is an online application"""
	recipient = doc.get("educore_applicant_user")
	if not recipient or not enabled():
		return
	subject, body = render(event, doc, **extra)
	_deliver(recipient, subject, body, doc)


def can_send() -> bool:
	return bool(frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}))


def _deliver(recipient: str, subject: str, body: str, doc):
	"""Queued; without an outgoing email account (e.g. a fresh site) it is noted on the timeline instead, so a
	missing mail setup never blocks a decision"""
	if not can_send():
		doc.add_comment("Info", _("Email not sent (no outgoing email account is set up): {0}").format(subject))
		return
	frappe.sendmail(
		recipients=[recipient],
		subject=subject,
		message=body,
		reference_doctype=doc.doctype,
		reference_name=doc.name,
	)


# --- from the application's on_update ------------------------------------------------------------------

#: new status: event (online applications)
ON_STATUS = {"Applied": "submitted", "Approved": "offer_made", "Rejected": "unsuccessful", "Declined": "offer_declined"}


def on_applicant_update(doc, method=None):
	if not doc.get("educore_applicant_user") or not doc.has_value_changed("application_status"):
		return
	before = doc.get_doc_before_save()
	event = ON_STATUS.get(doc.application_status)
	# "Applied" again after a reconsideration is not a new submission
	if event == "submitted" and before and before.application_status != "Draft":
		return
	if event:
		send(doc, event)
