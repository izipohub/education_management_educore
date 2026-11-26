"""Disciplinary cases: a student's misconduct reported, investigated, heard and decided, with a right of appeal.

1. Any member of staff reports what happened (the student, the day, what they saw, evidence): Reported.
2. The Student Affairs Officer of the student's campus looks into it (Investigating), and dismisses it (no case) or
   treats it as minor or serious. A minor case Student Affairs decides itself (a warning, a written warning or a fine).
   A serious one goes to the disciplinary committee: Student Affairs sets the charge and the hearing (the student is
   emailed: Hearing), then records the committee's finding, sanction and reasons.
3. Decided: the student is emailed the decision and may appeal in EduCore until the appeal date (the university's
   number of days, Discipline Settings). The Registrar decides the appeal: upheld, changed or overturned (Closed).

A sanction acts by itself: a suspension (from and until) or an expulsion stops the student registering while it lasts
(educore.registration.rules) and shows in their status history; a fine is invoiced to their fee account (cancelled,
when still unpaid, if the appeal overturns it or changes it). The student sees a case from its hearing or decision
on, never the investigation. Cases are confidential: the student's campus's Student Affairs and the Registrar.
"""

import os

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

REPORTED, INVESTIGATING, HEARING, DECIDED, APPEALED, CLOSED, DISMISSED = (
	"Reported", "Investigating", "Hearing", "Decided", "Appealed", "Closed", "Dismissed",
)
MINOR, SERIOUS = "Minor", "Serious"
RESPONSIBLE, NOT_RESPONSIBLE = "Responsible", "Not responsible"
WARNING, WRITTEN_WARNING, FINE, SUSPENSION, EXPULSION = "Warning", "Written warning", "Fine", "Suspension", "Expulsion"
#: what Student Affairs may decide itself; the rest is the committee's
MINOR_SANCTIONS = (WARNING, WRITTEN_WARNING, FINE)
SANCTIONS = (WARNING, WRITTEN_WARNING, FINE, SUSPENSION, EXPULSION)
UPHELD, CHANGED, OVERTURNED = "Upheld", "Changed", "Overturned"
#: the student sees the case from here on
SEEN_BY_STUDENT = (HEARING, DECIDED, APPEALED, CLOSED)
FINE_ITEM = "Disciplinary Fine"
DEFAULT_APPEAL_DAYS = 10


def ensure_defaults():
	if "appeal_days" not in frappe.db.sql_list("select field from `tabSingles` where doctype = 'Discipline Settings'"):
		frappe.db.set_single_value("Discipline Settings", "appeal_days", DEFAULT_APPEAL_DAYS)


def appeal_days() -> int:
	return cint(frappe.db.get_single_value("Discipline Settings", "appeal_days"))


def _note(value: str | None, message: str) -> str:
	value = (value or "").strip()
	if not value:
		frappe.throw(message)
	return value


def report(student: str, incident_date: str, incident: str, upload: tuple[bytes, str] | None = None) -> "frappe.model.document.Document":
	if getdate(incident_date) > getdate(nowdate()):
		frappe.throw(_("The incident date cannot be in the future"))
	incident = _note(incident, _("Say what happened"))
	if upload:
		extension = os.path.splitext(upload[1] or "")[1].lower()
		if extension not in (".pdf", ".jpg", ".jpeg", ".png") or not upload[0] or len(upload[0]) > 5 * 1024 * 1024:
			frappe.throw(_("Evidence is a PDF, JPG or PNG file of up to 5 MB"))
	doc = frappe.get_doc(
		{
			"doctype": "Disciplinary Case",
			"student": student,
			"status": REPORTED,
			"reported_by": frappe.session.user,
			"reported_on": now_datetime(),
			"incident_date": incident_date,
			"incident": incident,
		}
	).insert(ignore_permissions=True)
	if upload:
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{doc.name}-evidence{os.path.splitext(upload[1])[1].lower()}",
				"attached_to_doctype": "Disciplinary Case",
				"attached_to_name": doc.name,
				"is_private": 1,
				"content": upload[0],
			}
		).insert(ignore_permissions=True)
		doc.db_set("evidence", file.file_url)
	return doc


def _expect(doc, *statuses):
	if doc.status not in statuses:
		frappe.throw(_("This case is {0}").format(doc.status.lower()))


def investigate(doc):
	_expect(doc, REPORTED)
	doc.update({"status": INVESTIGATING, "investigated_by": frappe.session.user})
	doc.save(ignore_permissions=True)


def dismiss(doc, note: str):
	"""No case to answer: closed without the student being told (they never saw it)"""
	_expect(doc, REPORTED, INVESTIGATING)
	doc.update({"status": DISMISSED, "investigation_note": _note(note, _("Say why there is no case")), "investigated_by": doc.investigated_by or frappe.session.user})
	doc.save(ignore_permissions=True)


def schedule_hearing(doc, charge: str, hearing_on: str, venue: str, committee: str | None = None, note: str | None = None):
	"""A serious case to the committee: the charge and the hearing, the student emailed"""
	from educore.academics import notify

	_expect(doc, INVESTIGATING, HEARING)
	if getdate(hearing_on) < getdate(nowdate()):
		frappe.throw(_("The hearing is in the future"))
	doc.update(
		{
			"level": SERIOUS,
			"status": HEARING,
			"charge": _note(charge, _("Say what the student is charged with")),
			"hearing_on": hearing_on,
			"hearing_venue": _note(venue, _("Say where the hearing is")),
			"committee": (committee or "").strip() or None,
			"investigation_note": (note or "").strip() or doc.investigation_note,
		}
	)
	doc.save(ignore_permissions=True)
	notify.send(
		doc.student,
		"disciplinary_hearing",
		doc,
		charge=doc.charge,
		when=f"{notify.date(doc.hearing_on)} at {str(doc.hearing_on)[11:16]}",
		venue=doc.hearing_venue,
	)


def decide(doc, finding: str, sanction: str | None, reasons: str, fine: float = 0, suspended_from=None, suspended_until=None, hearing_note: str | None = None):
	"""The decision: by Student Affairs for a minor case, recorded for the committee after a hearing. Its sanction acts
	at once; the student is emailed it and the appeal date."""
	from educore.academics import notify
	from educore.finance import charges

	_expect(doc, INVESTIGATING, HEARING)
	minor = doc.status == INVESTIGATING
	if finding not in (RESPONSIBLE, NOT_RESPONSIBLE):
		frappe.throw(_("Record the finding"))
	reasons = _note(reasons, _("Give the reasons"))
	sanction = sanction or None
	if finding == NOT_RESPONSIBLE:
		sanction = None
	elif sanction not in SANCTIONS:
		frappe.throw(_("Choose the sanction"))
	if minor and sanction and sanction not in MINOR_SANCTIONS:
		frappe.throw(_("A suspension or an expulsion is decided by the disciplinary committee, after a hearing"))
	_check_sanction(sanction, fine, suspended_from, suspended_until)
	doc.update(
		{
			"level": MINOR if minor else SERIOUS,
			"status": DECIDED,
			"finding": finding,
			"sanction": sanction,
			"fine": flt(fine, 2) if sanction == FINE else 0,
			"suspended_from": suspended_from if sanction == SUSPENSION else None,
			"suspended_until": suspended_until if sanction == SUSPENSION else None,
			"decision_note": reasons,
			"hearing_note": (hearing_note or "").strip() or doc.hearing_note,
			"decided_by": frappe.session.user,
			"decided_on": nowdate(),
			"appeal_until": add_days(nowdate(), appeal_days()) if finding == RESPONSIBLE else None,
		}
	)
	doc.save(ignore_permissions=True)
	if doc.sanction == FINE:
		doc.db_set("fine_invoice", charges.invoice(doc.student, doc.campus, FINE_ITEM, _("Disciplinary fine"), doc.fine, _("Disciplinary case {0}").format(doc.name)))
	notify.send(
		doc.student,
		"disciplinary_decided",
		doc,
		outcome=describe(doc),
		reasons=doc.decision_note,
		appeal=_("You may appeal in EduCore until {0}.").format(notify.date(doc.appeal_until)) if doc.appeal_until else "",
	)


def _check_sanction(sanction, fine, suspended_from, suspended_until):
	if sanction == FINE and flt(fine) <= 0:
		frappe.throw(_("Give the fine"))
	if sanction == SUSPENSION:
		if not suspended_from or not suspended_until:
			frappe.throw(_("Give the suspension's first and last days"))
		if getdate(suspended_until) < getdate(suspended_from):
			frappe.throw(_("The suspension ends after it starts"))


def appeal(doc, reason: str):
	_expect(doc, DECIDED)
	if not doc.appeal_until or getdate(nowdate()) > getdate(doc.appeal_until):
		frappe.throw(_("The time to appeal has passed"))
	doc.update({"status": APPEALED, "appeal_reason": _note(reason, _("Give the grounds of your appeal")), "appealed_on": nowdate()})
	doc.save(ignore_permissions=True)


def decide_appeal(doc, outcome: str, note: str, sanction: str | None = None, fine: float = 0, suspended_from=None, suspended_until=None):
	"""The Registrar: the decision upheld, changed (a new sanction) or overturned; a fine no longer due is cancelled if
	unpaid (a fine paid is Finance's to refund), a changed fine invoiced"""
	from educore.academics import notify
	from educore.finance import charges

	_expect(doc, APPEALED)
	if outcome not in (UPHELD, CHANGED, OVERTURNED):
		frappe.throw(_("Choose the outcome of the appeal"))
	note = _note(note, _("Give the reasons"))
	if outcome == CHANGED:
		if sanction not in SANCTIONS:
			frappe.throw(_("Choose the new sanction"))
		_check_sanction(sanction, fine, suspended_from, suspended_until)
	if outcome in (CHANGED, OVERTURNED):
		charges.cancel_if_unpaid(doc.fine_invoice)
		changed = {
			"sanction": sanction if outcome == CHANGED else None,
			"finding": doc.finding if outcome == CHANGED else NOT_RESPONSIBLE,
			"fine": flt(fine, 2) if outcome == CHANGED and sanction == FINE else 0,
			"suspended_from": suspended_from if outcome == CHANGED and sanction == SUSPENSION else None,
			"suspended_until": suspended_until if outcome == CHANGED and sanction == SUSPENSION else None,
			"fine_invoice": None,
		}
		doc.update(changed)
	doc.update({"status": CLOSED, "appeal_outcome": outcome, "appeal_note": note, "appeal_decided_by": frappe.session.user, "appeal_decided_on": nowdate()})
	doc.save(ignore_permissions=True)
	if doc.sanction == FINE and outcome == CHANGED:
		doc.db_set("fine_invoice", charges.invoice(doc.student, doc.campus, FINE_ITEM, _("Disciplinary fine"), doc.fine, _("Disciplinary case {0}, after appeal").format(doc.name)))
	notify.send(doc.student, "disciplinary_appeal_decided", doc, outcome=_(outcome).lower(), now=describe(doc), reasons=note)


def describe(doc) -> str:
	"""The outcome in words"""
	if doc.finding == NOT_RESPONSIBLE:
		return _("Not responsible")
	if doc.sanction == FINE:
		return _("Fine of N$ {0}").format(frappe.utils.fmt_money(doc.fine, precision=2))
	if doc.sanction == SUSPENSION:
		return _("Suspension from {0} to {1}").format(frappe.utils.formatdate(doc.suspended_from), frappe.utils.formatdate(doc.suspended_until))
	return _(doc.sanction or "")


def barring(student: str, on=None) -> list[str]:
	"""The suspensions and expulsions in force for the student (on a day, else today), in words"""
	on = getdate(on or nowdate())
	out = []
	for c in frappe.get_all(
		"Disciplinary Case",
		filters={"student": student, "status": ("in", (DECIDED, APPEALED, CLOSED)), "sanction": ("in", (SUSPENSION, EXPULSION))},
		fields=["sanction", "suspended_from", "suspended_until"],
	):
		if c.sanction == EXPULSION:
			out.append(_("Expelled after a disciplinary decision"))
		elif c.suspended_until and getdate(c.suspended_until) >= on:
			out.append(_("Suspended until {0} after a disciplinary decision").format(frappe.utils.formatdate(c.suspended_until)))
	return out
