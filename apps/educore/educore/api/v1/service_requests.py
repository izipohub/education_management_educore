"""Service requests (educore.academics.service_requests): the student asks and follows; each office works its queue;
the Registrar keeps the categories.

Who the student is comes only from the session. An office sees the requests of its categories, for the students its
User Permissions let it read (campus, faculty); one that cannot read students at all sees its campuses' requests.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from educore.academics import service_requests as sr

SETUP_ROLES = ("Registrar", "System Manager")
STATUSES = (sr.SUBMITTED, sr.IN_PROGRESS, sr.RESOLVED, sr.DECLINED, sr.WITHDRAWN)


def _student() -> str:
	name = frappe.db.get_value("Student", {"user": frappe.session.user, "enabled": 1})
	if not name:
		frappe.throw(_("This page is for students."), frappe.PermissionError)
	return name


def _upload() -> tuple[bytes, str] | None:
	upload = frappe.request.files.get("file") if frappe.request and frappe.request.files else None
	return (upload.stream.read(), upload.filename) if upload and upload.filename else None


def _mine(name: str):
	doc = frappe.get_doc("Service Request", name)
	if doc.student != _student():
		frappe.throw(_("This is not your request"), frappe.PermissionError)
	return doc


# --- the student --------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def mine() -> dict:
	student = _student()
	return {
		"categories": frappe.get_all(
			"Service Request Category",
			filters={"disabled": 0},
			fields=["name", "office", "response_days", "fee", "needs_attachment", "guidance"],
			order_by="name asc",
		),
		"requests": [
			sr.serialise(frappe.get_doc("Service Request", n), for_student=True)
			for n in frappe.get_all("Service Request", filters={"student": student}, pluck="name", order_by="creation desc")
		],
	}


@frappe.whitelist(methods=["POST"])
def ask(category: str, details: str) -> dict:
	"""A new request (multipart, with an optional "file")"""
	doc = sr.ask(_student(), category, details, _upload())
	return sr.serialise(frappe.get_doc("Service Request", doc.name), for_student=True)


@frappe.whitelist(methods=["POST"])
def write_mine(name: str, message: str) -> dict:
	doc = _mine(name)
	sr.write(doc, message, from_student=True, upload=_upload())
	return sr.serialise(doc, for_student=True)


@frappe.whitelist(methods=["POST"])
def withdraw(name: str) -> dict:
	doc = _mine(name)
	sr.withdraw(doc)
	return sr.serialise(doc, for_student=True)


# --- the offices --------------------------------------------------------------------------------------


def _offices() -> list[str]:
	offices = sr.offices_of()
	if not offices:
		frappe.throw(_("Service requests are handled by the university's offices"), frappe.PermissionError)
	return offices


def _in_scope(rows: list) -> list:
	if not rows:
		return []
	if frappe.has_permission("Student", "read"):
		readable = set(frappe.get_list("Student", filters={"name": ("in", list({r.student for r in rows}))}, pluck="name", limit=0))
		return [r for r in rows if r.student in readable]
	from educore.access.scope import campuses

	mine = campuses()
	return [r for r in rows if r.campus in mine]


def _handled(name: str):
	rows = _in_scope(frappe.get_all("Service Request", filters={"name": name, "office": ("in", _offices())}, fields=["name", "student", "campus"]))
	if not rows:
		frappe.throw(_("This request is not for your office"), frappe.PermissionError)
	return frappe.get_doc("Service Request", name)


@frappe.whitelist(methods=["GET"])
def queue() -> dict:
	"""Every request for this person's offices, open first and oldest first; the page filters by status"""
	offices = _offices()
	rows = _in_scope(
		frappe.get_all(
			"Service Request",
			filters={"office": ("in", offices)},
			fields=["name", "student", "student_name", "campus", "category", "office", "status", "submitted_on", "due_on", "assigned_to"],
			order_by="submitted_on asc",
			limit=0,
		)
	)
	out = []
	for r in rows:
		out.append(
			{
				**{k: r[k] for k in ("name", "student", "student_name", "campus", "category", "office", "status")},
				"submitted_on": str(r.submitted_on) if r.submitted_on else None,
				"due_on": str(r.due_on) if r.due_on else None,
				"overdue": sr.overdue(r),
				"assigned_to": frappe.utils.get_fullname(r.assigned_to) if r.assigned_to else None,
				"mine": r.assigned_to == frappe.session.user,
			}
		)
	return {"rows": out, "offices": offices}


@frappe.whitelist(methods=["GET"])
def request(name: str) -> dict:
	return {**sr.serialise(_handled(name)), "can_act": True}


@frappe.whitelist(methods=["POST"])
def take(name: str) -> dict:
	doc = _handled(name)
	sr.take(doc)
	return request(name)


@frappe.whitelist(methods=["POST"])
def write(name: str, message: str) -> dict:
	doc = _handled(name)
	sr.write(doc, message, from_student=False, upload=_upload())
	return request(name)


@frappe.whitelist(methods=["POST"])
def resolve(name: str, note: str | None = None) -> dict:
	doc = _handled(name)
	sr.close(doc, sr.RESOLVED, note or "")
	return request(name)


@frappe.whitelist(methods=["POST"])
def decline(name: str, note: str) -> dict:
	doc = _handled(name)
	sr.close(doc, sr.DECLINED, note)
	return request(name)


# --- the documents ------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def document(name: str, message: int | str | None = None):
	"""The request's document (or a message's), to the student it belongs to or the office handling it"""
	is_student = bool(frappe.db.get_value("Student", {"user": frappe.session.user}))
	doc = _mine(name) if is_student else _handled(name)
	url = doc.attachment if not message else next((m.attachment for m in doc.messages if m.idx == cint(message)), None)
	if not url:
		frappe.throw(_("No document"), frappe.DoesNotExistError)
	file = frappe.get_doc("File", {"file_url": url})
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"


# --- the categories (Registrar) -----------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def categories() -> dict:
	if not set(frappe.get_roles()) & set((*SETUP_ROLES, *sr.OFFICES.values())):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return {
		"rows": frappe.get_all(
			"Service Request Category",
			fields=["name", "office", "response_days", "fee", "needs_attachment", "guidance", "disabled"],
			order_by="disabled asc, name asc",
		),
		"offices": list(sr.OFFICES),
		"can_edit": bool(set(frappe.get_roles()) & set(SETUP_ROLES)),
	}


@frappe.whitelist(methods=["POST"])
def save_category(data: dict | str) -> dict:
	"""A category added or changed; one already asked for keeps its name (mark it not in use and add another)"""
	if not set(frappe.get_roles()) & set(SETUP_ROLES):
		frappe.throw(_("Service request categories are the Registrar's"), frappe.PermissionError)
	data = frappe.parse_json(data)
	name = (data.get("name") or "").strip()
	new_name = (data.get("category_name") or name).strip()
	if not new_name:
		frappe.throw(_("Name the category"))
	if data.get("office") not in sr.OFFICES:
		frappe.throw(_("Choose the office that handles it"))
	if cint(data.get("response_days")) < 0 or flt(data.get("fee")) < 0:
		frappe.throw(_("Days and fee cannot be negative"))
	values = {
		"office": data["office"],
		"response_days": cint(data.get("response_days")),
		"fee": flt(data.get("fee"), 2),
		"needs_attachment": cint(data.get("needs_attachment")),
		"guidance": (data.get("guidance") or "").strip() or None,
		"disabled": cint(data.get("disabled")),
	}
	if name:
		doc = frappe.get_doc("Service Request Category", name)
		if new_name != name:
			frappe.throw(_("A category keeps its name: mark it not in use and add another"))
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		if frappe.db.exists("Service Request Category", new_name):
			frappe.throw(_("{0} exists already").format(new_name))
		frappe.get_doc({"doctype": "Service Request Category", "category_name": new_name, **values}).insert(ignore_permissions=True)
	return categories()
