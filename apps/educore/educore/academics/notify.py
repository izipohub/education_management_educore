"""Emails to students about decisions on their studies.

Sent when Registration Settings say so (notify_students), to the student's login email (else their student email),
queued through Frappe's Email Queue with the deciding record as the reference, so each email also shows on that
record's timeline. Without an outgoing email account, a note goes on the timeline instead and the decision stands
(educore.admissions.notify._deliver).
"""

import frappe
from frappe import _
from frappe.utils import escape_html, formatdate

from educore.admissions.notify import _deliver, university

#: event: (subject, paragraphs, page in the app, office signing); {placeholders} are filled from the caller
TEMPLATES = {
	"registration_approved": (
		"Registration {academic_year} approved",
		[
			"Dear {first_name},",
			"Your registration for {academic_year} in the {programme} is approved. Your fees for the year are on your "
			"fee statement, and your proof of registration is on My studies.",
		],
		"my-studies",
		"Faculty Office",
	),
	"registration_returned": (
		"Registration {academic_year}: changes needed",
		[
			"Dear {first_name},",
			"The faculty officer has returned your registration for {academic_year}: {note}",
			"Please make the change and submit your registration again.",
		],
		"registration",
		"Faculty Office",
	),
	"course_change_approved": (
		"Course change approved",
		["Dear {first_name},", "Your course change is approved: {changes}."],
		"registration",
		"Faculty Office",
	),
	"course_change_declined": (
		"Course change declined",
		["Dear {first_name},", "Your course change ({changes}) is declined: {note}"],
		"registration",
		"Faculty Office",
	),
	"interruption_approved": (
		"Interruption of studies approved",
		[
			"Dear {first_name},",
			"Your request to interrupt your studies is approved, with {last_day} as your last day attending. You "
			"register again for {return_year}.",
			"The Finance Office will contact you about any fees.",
		],
		"my-studies",
		"Office of the Registrar",
	),
	"cancellation_approved": (
		"Cancellation of studies approved",
		[
			"Dear {first_name},",
			"Your request to cancel your studies is approved, with {last_day} as your last day attending. To study "
			"again, you apply again.",
			"The Finance Office will contact you about any fees.",
		],
		"my-studies",
		"Office of the Registrar",
	),
	"studies_request_declined": (
		"Request about your studies declined",
		["Dear {first_name},", "Your request to {what} is declined: {note}"],
		"my-studies",
		"Office of the Registrar",
	),
	"results_published": (
		"Results published",
		["Dear {first_name},", "Your results for {courses} are published.", "They are on My studies."],
		"my-studies",
		"Examinations Office",
	),
	"supplementary_published": (
		"Supplementary examination results published",
		["Dear {first_name},", "Your result for {courses} after the supplementary sitting is published.", "It is on My studies."],
		"my-studies",
		"Examinations Office",
	),
	"programme_completed": (
		"Programme completed: {programme}",
		[
			"Dear {first_name},",
			"Congratulations. The completion of your {programme} was approved by the {reference} on {completed_on}.",
			"The Office of the Registrar will contact you about the graduation ceremony and your certificate.",
		],
		"my-studies",
		"Office of the Registrar",
	),
}


def enabled() -> bool:
	return bool(frappe.get_cached_doc("Registration Settings").get("notify_students"))


def app_url(page: str) -> str:
	base = frappe.conf.get("educore_app_url") or frappe.utils.get_url()
	return f"{base.rstrip('/')}/{page}"


def _recipient(student: str) -> tuple[str | None, str]:
	user, email, first, name = frappe.db.get_value("Student", student, ["user", "student_email_id", "first_name", "student_name"])
	return user or email, first or name


def render(event: str, first_name: str, **context) -> tuple[str, str]:
	subject, paragraphs, page, office = TEMPLATES[event]
	values = {k: escape_html(str(v)) if v is not None else "" for k, v in {"first_name": first_name, **context}.items()}
	body = "".join(f"<p>{_(p).format(**values)}</p>" for p in paragraphs)
	body += f'<p><a href="{app_url(page)}">{_("Open EduCore")}</a></p>'
	body += f"<p>{_(office)}<br>{escape_html(university())}</p>"
	return _(subject).format(**{k: str(v) for k, v in context.items()}), body


def send(student: str, event: str, record, **context):
	"""Queue the email for this event to the student, if the university emails students"""
	if not enabled():
		return
	recipient, first_name = _recipient(student)
	if not recipient:
		return
	subject, body = render(event, first_name, **context)
	_deliver(recipient, subject, body, record)


def date(value) -> str:
	return formatdate(value, "dd MMMM yyyy") if value else ""


def courses(names: list[str]) -> str:
	names = sorted(set(names))
	return names[0] if len(names) == 1 else _("{0} and {1}").format(", ".join(names[:-1]), names[-1])
