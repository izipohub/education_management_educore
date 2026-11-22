"""Offers on online applications (docs/architecture/online-applications.md, phase 3).

Approving an online application makes an offer: the applicant has the university's number of days (Admission
Settings) to accept or decline it in the applicant portal. Declining moves the application to Declined; an
unanswered offer lapses after the deadline (daily job) to Lapsed. Both free the place, since intake capacity counts
Approved and Admitted applications only. The registrar can reconsider either. Accepting keeps the application
Approved, marked Accepted; enrolment then needs an accepted offer when the university says so.

A paper application captured by staff has no applicant login: its offer is answered in person, so none of this
applies to it.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, now_datetime, nowdate

AWAITING, ACCEPTED, DECLINED, LAPSED = "Awaiting response", "Accepted", "Declined", "Lapsed"


def _settings():
	return frappe.get_cached_doc("Admission Settings")


def is_online(doc) -> bool:
	return bool(doc.get("educore_applicant_user"))


def on_approved(doc):
	"""Called while an application becomes Approved: the offer and its deadline"""
	if not is_online(doc):
		return
	days = _settings().offer_response_days or 14
	doc.educore_offer_status = AWAITING
	doc.educore_offer_deadline = add_days(nowdate(), days)
	doc.educore_offer_responded_on = None
	doc.educore_offer_reminded = 0
	doc.educore_offer_decline_reason = None


def on_reconsidered(doc):
	"""Back to Applied: any earlier offer no longer stands"""
	for field in ("educore_offer_status", "educore_offer_deadline", "educore_offer_responded_on", "educore_offer_decline_reason"):
		doc.set(field, None)
	doc.educore_offer_reminded = 0


def check_open(doc):
	if doc.application_status != "Approved" or doc.get("educore_offer_status") != AWAITING:
		frappe.throw(_("There is no offer awaiting your response"))
	if doc.educore_offer_deadline and getdate(doc.educore_offer_deadline) < getdate(nowdate()):
		frappe.throw(_("The deadline for this offer has passed"))


def accept(doc):
	check_open(doc)
	doc.db_set({"educore_offer_status": ACCEPTED, "educore_offer_responded_on": now_datetime()})
	doc.add_comment("Info", _("Offer accepted online"))
	from educore.admissions import notify

	notify.send(doc, "offer_accepted")


def decline(doc, reason: str | None = None):
	"""The workflow's "Decline Offer" (Approved → Declined), as the applicant. Saved like their Submit: the
	workflow checks that the Applicant role may make this transition; applicants have no write permission."""
	check_open(doc)
	doc.application_status = "Declined"
	doc.educore_offer_status = DECLINED
	doc.educore_offer_responded_on = now_datetime()
	doc.educore_offer_decline_reason = (reason or "").strip() or None
	doc.flags.ignore_permissions = True
	doc.save()
	doc.add_comment("Workflow", _("Offer declined online"))


def needs_acceptance(doc) -> bool:
	"""Whether enrolment must wait for the applicant to accept"""
	return is_online(doc) and bool(_settings().enrolment_needs_acceptance) and doc.get("educore_offer_status") != ACCEPTED


def extend(doc, deadline: str):
	if doc.application_status != "Approved" or doc.get("educore_offer_status") != AWAITING:
		frappe.throw(_("Only an offer awaiting a response can be extended"))
	if getdate(deadline) < getdate(nowdate()):
		frappe.throw(_("The new deadline cannot be in the past"))
	old = doc.educore_offer_deadline
	doc.db_set({"educore_offer_deadline": getdate(deadline), "educore_offer_reminded": 0})
	doc.add_comment("Info", _("Offer deadline changed from {0} to {1}").format(old, deadline))


# --- the daily job -------------------------------------------------------------------------------------


def daily():
	remind()
	lapse()


def _awaiting():
	return frappe.get_all(
		"Student Applicant",
		filters={"application_status": "Approved", "educore_offer_status": AWAITING, "educore_offer_deadline": ("is", "set")},
		fields=["name", "educore_offer_deadline", "educore_offer_reminded"],
	)


def remind() -> int:
	days = _settings().offer_reminder_days or 0
	if not days:
		return 0
	sent = 0
	from educore.admissions import notify

	for row in _awaiting():
		left = date_diff(row.educore_offer_deadline, nowdate())
		if 0 <= left <= days and not row.educore_offer_reminded:
			doc = frappe.get_doc("Student Applicant", row.name)
			notify.send(doc, "offer_reminder")
			doc.db_set("educore_offer_reminded", 1)
			sent += 1
	return sent


def lapse() -> int:
	"""Offers past their deadline: Lapsed, the place released. Set directly, as no person acts."""
	lapsed = 0
	from educore.admissions import notify

	for row in _awaiting():
		if getdate(row.educore_offer_deadline) >= getdate(nowdate()):
			continue
		doc = frappe.get_doc("Student Applicant", row.name)
		doc.db_set({"application_status": "Lapsed", "educore_offer_status": LAPSED})
		doc.add_comment("Workflow", _("Lapsed: the offer was not answered by {0}").format(row.educore_offer_deadline))
		notify.send(doc, "offer_lapsed")
		lapsed += 1
	return lapsed
