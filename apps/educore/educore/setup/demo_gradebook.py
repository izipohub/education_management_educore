"""A demo gradebook (development only): FIN2511 at Keetmanshoop, its lecturer's two tests and two assignments, and the
class's scores (a student with an assignment still to mark has no CA yet). Runs from demo_students.create after the
mark sheets."""

import frappe

from educore.academics import gradebook

GROUP = "FIN2511 KMP 2026"
PLAN = [
	{"title": "Test 1", "kind": "Test", "out_of": 50, "weight": 25},
	{"title": "Test 2", "kind": "Test", "out_of": 50, "weight": 25},
	{"title": "Assignment 1", "kind": "Assignment", "out_of": 100, "weight": 25},
	{"title": "Assignment 2", "kind": "Assignment", "out_of": 100, "weight": 25},
]
#: student name: scores in the order of the plan (None: not marked yet)
SCORES = {"Anna Beukes": (38, 41, 72, 80), "Petrus Kooper": (29, 33, 64, None)}


def create() -> int:
	if not frappe.db.exists("Student Group", GROUP):
		return 0
	name = frappe.db.get_value("Mark Sheet", {"student_group": GROUP})
	if name and frappe.get_doc("Mark Sheet", name).get("assessments"):
		return 0
	if not name:
		g = frappe.get_doc("Student Group", GROUP)
		doc = frappe.get_doc(
			{
				"doctype": "Mark Sheet",
				"student_group": GROUP,
				"course": g.course,
				"campus": g.get("campus"),
				"academic_year": g.academic_year,
				"status": "Draft",
				"entries": [{"student": s.student, "student_name": s.student_name} for s in g.students if s.active],
			}
		).insert(ignore_permissions=True)
	else:
		doc = frappe.get_doc("Mark Sheet", name)
	if doc.status != "Draft":
		return 0
	gradebook.save(doc, PLAN, {})
	keys = [a.assessment_key for a in doc.assessments]
	names = {e.student_name: e.student for e in doc.entries}
	given = {names[n]: {k: v for k, v in zip(keys, marks) if v is not None} for n, marks in SCORES.items() if n in names}
	gradebook.save(doc, [a.as_dict() for a in doc.assessments], given)
	doc.save(ignore_permissions=True)
	return 1
