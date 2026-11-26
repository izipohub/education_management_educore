"""Assessment types, for the faculty: the kinds of continuous assessment its lecturers may plan
(educore.academics.assessment_types).

The Dean keeps the faculty's list: adds a type, says whether it is taken online in Moodle and the most it may count
for in a module's CA, and marks one no longer in use (types are not deleted: plans use them by name, and a type
already used keeps its name). The department, the faculty officer and the examinations office read it.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from educore.academics import assessment_types

EDIT_ROLES = ("Dean", "System Manager")
READ_ROLES = (*EDIT_ROLES, "Head of Department", "Faculty Officer", "Registrar", "Examinations Officer", "Quality Assurance Officer", "Executive Management")


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _faculties() -> list[str]:
	"""The faculties this person may see: of their department or faculty (User Permissions), else all"""
	units = frappe.get_list("Department", filters={"educore_unit_type": ("in", ("Faculty", "School", "Academic Department"))}, pluck="name", limit=0)
	return sorted({f for f in (assessment_types.faculty_of(u) for u in units) if f})


def _used(name: str) -> bool:
	return bool(frappe.db.exists("Mark Sheet Assessment", {"parenttype": "Mark Sheet", "kind": name}))


@frappe.whitelist(methods=["GET"])
def types() -> dict:
	if not _has(READ_ROLES):
		frappe.throw(_("Assessment types are the faculty's"), frappe.PermissionError)
	faculties = _faculties()
	return {
		"faculties": [
			{
				"faculty": f,
				"label": f.rsplit(" - ", 1)[0],
				"types": [{**t, "used": _used(t.type_name)} for t in assessment_types.of_faculty(f, include_disabled=True)],
			}
			for f in faculties
		],
		"can_edit": _has(EDIT_ROLES),
	}


@frappe.whitelist(methods=["POST"])
def save(faculty: str, rows: list | str) -> dict:
	"""The faculty's list as the Dean leaves it: types changed, added, or marked not in use"""
	if not _has(EDIT_ROLES):
		frappe.throw(_("The faculty's assessment types are the Dean's"), frappe.PermissionError)
	if faculty not in _faculties():
		frappe.throw(_("This is not your faculty"), frappe.PermissionError)
	rows = frappe.parse_json(rows) or []
	names = [(r.get("type_name") or "").strip().lower() for r in rows]
	if len(set(names)) != len(names):
		frappe.throw(_("Each type has its own name"))
	existing = {t.name: t for t in assessment_types.of_faculty(faculty, include_disabled=True)}
	for r in rows:
		values = {
			"type_name": (r.get("type_name") or "").strip(),
			"online": cint(r.get("online")),
			"max_share": flt(r.get("max_share")),
			"disabled": cint(r.get("disabled")),
		}
		if not values["type_name"]:
			frappe.throw(_("Name each type"))
		if r.get("name"):
			if r["name"] not in existing:
				frappe.throw(_("{0} is not one of this faculty's types").format(r["name"]))
			doc = frappe.get_doc("Assessment Type", r["name"])
			if doc.type_name != values["type_name"] and _used(doc.type_name):
				frappe.throw(_("{0} is used in assessment plans: mark it not in use and add the new one").format(doc.type_name))
			doc.update(values)
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Assessment Type", "faculty": faculty, **values}).insert(ignore_permissions=True)
	if not any(not cint(r.get("disabled")) for r in rows):
		frappe.throw(_("Keep at least one type in use"))
	return types()
