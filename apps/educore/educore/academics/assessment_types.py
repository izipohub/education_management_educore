"""Assessment types: the kinds of continuous assessment a faculty's lecturers may plan, kept by the Dean.

Each faculty (or a school outside a faculty) has its own list (Assessment Type): a test, an assignment, an online
quiz... A type may be taken online in Moodle (its assessments are linked to a Moodle activity and their scores
brought in from it, educore.learning.moodle_grades) and may have a highest share of the CA, which the module's
assessments of that type may not pass together. A type no longer used is marked so; plans already using it keep it.

Every faculty starts with a standard list (made on migrate, and when a faculty is added), which the Dean changes on
the Examinations screen (educore.api.v1.assessment_types). The lecturer's plan is checked against it
(educore.academics.gradebook).
"""

import frappe
from frappe import _
from frappe.utils import flt

#: the list a faculty starts with: (type, online in Moodle)
STANDARD = (
	("Test", 0),
	("Quiz", 0),
	("Assignment", 0),
	("Project", 0),
	("Practical", 0),
	("Presentation", 0),
	("Online quiz", 1),
	("Online assignment", 1),
)


def faculty_of(department: str | None) -> str | None:
	"""The faculty a department belongs to (itself if it is one); a school outside a faculty is its own"""
	found, unit = None, department
	while unit:
		kind, parent = frappe.get_cached_value("Department", unit, ["educore_unit_type", "parent_department"]) or (None, None)
		if kind == "Faculty":
			return unit
		if kind in ("School", "Academic Department"):
			found = unit if kind == "School" else found
		elif found:
			return found
		unit = parent
	return found


def faculty_of_course(course: str) -> str | None:
	return faculty_of(frappe.db.get_value("Course", course, "department"))


def faculties() -> list[str]:
	"""Every faculty, and every school outside one"""
	units = frappe.get_all("Department", filters={"educore_unit_type": ("in", ("Faculty", "School"))}, pluck="name")
	return sorted(u for u in units if faculty_of(u) == u)


def ensure_defaults(faculty: str | None = None):
	"""The standard list for each faculty that has none yet"""
	for unit in [faculty] if faculty else faculties():
		if frappe.db.exists("Assessment Type", {"faculty": unit}):
			continue
		for name, online in STANDARD:
			frappe.get_doc({"doctype": "Assessment Type", "type_name": name, "faculty": unit, "online": online}).insert(ignore_permissions=True)


def on_department_update(doc, method=None):
	"""A faculty added: its standard list"""
	if doc.get("educore_unit_type") in ("Faculty", "School") and faculty_of(doc.name) == doc.name:
		ensure_defaults(doc.name)


def validate(doc, method=None):
	doc.type_name = (doc.type_name or "").strip()
	if faculty_of(doc.faculty) != doc.faculty:
		frappe.throw(_("Assessment types belong to a faculty"))
	if frappe.db.exists("Assessment Type", {"faculty": doc.faculty, "type_name": doc.type_name, "name": ("!=", doc.name)}):
		frappe.throw(_("{0} already has {1}").format(doc.faculty.rsplit(" - ", 1)[0], doc.type_name))
	if not 0 <= flt(doc.max_share) <= 100:
		frappe.throw(_("The highest share is between 0 and 100%"))


def of_faculty(faculty: str | None, include_disabled: bool = False) -> list[dict]:
	if not faculty:
		return []
	return frappe.get_all(
		"Assessment Type",
		filters={"faculty": faculty, **({} if include_disabled else {"disabled": 0})},
		fields=["name", "type_name", "online", "max_share", "disabled"],
		order_by="online asc, type_name asc",
	)


def check_plan(course: str, assessments: list[dict], kept: set[str] = frozenset()):
	"""Each assessment of one of the faculty's types in use (or one the plan already had), and no type above its share"""
	types = {t.type_name: t for t in of_faculty(faculty_of_course(course), include_disabled=True)}
	shares: dict[str, float] = {}
	for a in assessments:
		kind = a.get("kind")
		t = types.get(kind)
		if not t or (t.disabled and kind not in kept):
			frappe.throw(_("{0}: choose one of the faculty's assessment types").format(a.get("title")))
		shares[kind] = shares.get(kind, 0) + flt(a.get("weight"))
		if a.get("moodle_cmid") and not t.online:
			frappe.throw(_("{0}: only an online assessment is linked to Moodle").format(a.get("title")))
	for kind, share in shares.items():
		limit = flt(types[kind].max_share)
		if limit and share > limit + 0.01:
			frappe.throw(_("{0} counts for {1}% of the CA; the faculty allows {2}% at most").format(kind, round(share, 2), f"{limit:g}"))


def online(course: str) -> set[str]:
	return {t.type_name for t in of_faculty(faculty_of_course(course), include_disabled=True) if t.online}
