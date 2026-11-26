"""Demo gradebooks (development only): FIN2511 at Keetmanshoop, its lecturer's two tests and two assignments approved
by the Head of Department, and the class's scores (a student with an assignment still to mark has no CA yet); and
CMP2521 at Oshakati, whose plan (with an online quiz in Moodle) waits for the department's approval. Runs from
demo_students.create after the mark sheets."""

import frappe

from frappe.utils import now_datetime

from educore.academics import gradebook

GROUP = "FIN2511 KMP 2026"
PLAN = [
	{"title": "Test 1", "kind": "Test", "out_of": 50, "weight": 25, "due_date": "2026-08-14"},
	{"title": "Test 2", "kind": "Test", "out_of": 50, "weight": 25, "due_date": "2026-09-25"},
	{"title": "Assignment 1", "kind": "Assignment", "out_of": 100, "weight": 25, "due_date": "2026-08-28"},
	{"title": "Assignment 2", "kind": "Assignment", "out_of": 100, "weight": 25, "due_date": "2026-10-09"},
]
#: student name: scores in the order of the plan (None: not marked yet)
SCORES = {"Anna Beukes": (38, 41, 72, 80), "Petrus Kooper": (29, 33, 64, None)}
APPROVED_BY = "head-of-department.accf@educore.localhost"

PROPOSED_GROUP = "CMP2521 OSH 2026"
PROPOSED_PLAN = [
	{"title": "Test 1", "kind": "Test", "out_of": 50, "weight": 30, "due_date": "2026-08-21"},
	{"title": "Online quiz", "kind": "Online quiz", "out_of": 20, "weight": 20, "due_date": "2026-09-11"},
	{"title": "Project", "kind": "Project", "out_of": 100, "weight": 50, "due_date": "2026-10-16"},
]


def create() -> int:
	return _approved() + _proposed()


def _draft_sheet(group: str):
	"""The class's mark sheet, still with the lecturer and without a plan (None: nothing to do)"""
	if not frappe.db.exists("Student Group", group):
		return None
	name = frappe.db.get_value("Mark Sheet", {"student_group": group})
	if name and frappe.get_doc("Mark Sheet", name).get("assessments"):
		return None
	if not name:
		g = frappe.get_doc("Student Group", group)
		doc = frappe.get_doc(
			{
				"doctype": "Mark Sheet",
				"student_group": group,
				"course": g.course,
				"campus": g.get("campus"),
				"academic_year": g.academic_year,
				"status": "Draft",
				"entries": [{"student": s.student, "student_name": s.student_name} for s in g.students if s.active],
			}
		).insert(ignore_permissions=True)
	else:
		doc = frappe.get_doc("Mark Sheet", name)
	return doc if doc.status == "Draft" else None


def _approved() -> int:
	doc = _draft_sheet(GROUP)
	if not doc:
		return 0
	gradebook.save(doc, PLAN, {})
	doc.update(
		{
			"plan_status": gradebook.APPROVED,
			"plan_approved_by": APPROVED_BY if frappe.db.exists("User", APPROVED_BY) else "Administrator",
			"plan_approved_on": now_datetime(),
		}
	)
	keys = [a.assessment_key for a in doc.assessments]
	names = {e.student_name: e.student for e in doc.entries}
	given = {names[n]: {k: v for k, v in zip(keys, marks) if v is not None} for n, marks in SCORES.items() if n in names}
	gradebook.save(doc, [a.as_dict() for a in doc.assessments], given)
	doc.save(ignore_permissions=True)
	return 1


def _proposed() -> int:
	doc = _draft_sheet(PROPOSED_GROUP)
	if not doc:
		return 0
	gradebook.save(doc, PROPOSED_PLAN, {})
	gradebook.propose(doc)
	doc.save(ignore_permissions=True)
	return 1
