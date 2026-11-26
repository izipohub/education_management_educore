"""The gradebook: a module's continuous assessments and each student's scores, from which the CA mark is worked out.

The lecturer decides the module's assessments (two tests and two assignments, two quizzes, a project...): each is
marked out of what the lecturer chooses and carries a share of the CA, the shares adding up to 100%. A student's CA
mark is the weighted sum of their scores, once every assessment is scored (a missed assessment is scored 0); it then
goes into the mark sheet like a CA typed in (educore.academics.results), and the final mark is worked out with the
examination as before. A module without assessments keeps its CA typed in directly.

The gradebook belongs to the mark sheet: it can be changed while the marks are with the lecturer, and is locked when
they are submitted.
"""

import frappe
from frappe import _
from frappe.utils import flt

from educore.academics import results

KINDS = ("Test", "Assignment", "Quiz", "Project", "Practical", "Presentation", "Other")


def uses_gradebook(doc) -> bool:
	return bool(doc.get("assessments"))


def validate_plan(assessments: list[dict]):
	titles = set()
	for a in assessments:
		title = (a.get("title") or "").strip()
		if not title:
			frappe.throw(_("Name each assessment"))
		if title.lower() in titles:
			frappe.throw(_("Two assessments are called {0}").format(title))
		titles.add(title.lower())
		if a.get("kind") not in KINDS:
			frappe.throw(_("Choose the kind of {0}").format(title))
		if flt(a.get("out_of")) <= 0:
			frappe.throw(_("{0}: say what it is marked out of").format(title))
		if flt(a.get("weight")) <= 0:
			frappe.throw(_("{0}: give its share of the CA").format(title))
	total = sum(flt(a.get("weight")) for a in assessments)
	if assessments and abs(total - 100) > 0.01:
		frappe.throw(_("The assessments add up to {0}% of the CA, not 100%").format(round(total, 2)))


def scores_of(doc) -> dict[str, dict[str, float | None]]:
	out: dict[str, dict] = {}
	for s in doc.get("scores") or []:
		out.setdefault(s.student, {})[s.assessment_key] = results.mark(s.score)
	return out


def ca_of(doc, student: str, scores: dict | None = None) -> float | None:
	"""The student's CA from the gradebook: the weighted sum of their scores, once every assessment is scored"""
	mine = (scores if scores is not None else scores_of(doc)).get(student, {})
	total = 0.0
	for a in doc.assessments:
		score = mine.get(a.assessment_key)
		if score is None:
			return None
		total += score / flt(a.out_of) * flt(a.weight)
	return round(total, 1)


def apply(doc):
	"""Each student's CA from the gradebook into the mark sheet, then the results worked out"""
	if not uses_gradebook(doc):
		return
	scores = scores_of(doc)
	for entry in doc.entries:
		entry.ca_mark = results.store(ca_of(doc, entry.student, scores))


def save(doc, assessments: list[dict], scores: dict[str, dict]):
	"""The lecturer's assessments (kept by key, new ones keyed) and the scores given (student: key: score)"""
	validate_plan(assessments)
	keep = []
	for a in assessments:
		key = a.get("assessment_key") or frappe.generate_hash(length=8)
		keep.append(
			{
				"assessment_key": key,
				"title": a["title"].strip(),
				"kind": a["kind"],
				"out_of": flt(a["out_of"]),
				"weight": flt(a["weight"]),
				"due_date": a.get("due_date") or None,
			}
		)
	doc.set("assessments", keep)
	keys = {a["assessment_key"]: a for a in keep}
	students = {e.student: e.student_name for e in doc.entries}
	current = scores_of(doc)
	for student, given in (scores or {}).items():
		if student not in students:
			frappe.throw(_("{0} is not in this module").format(student))
		for key, value in (given or {}).items():
			if key not in keys:
				continue
			number = results.mark(value)
			if number is not None and not 0 <= number <= keys[key]["out_of"]:
				frappe.throw(
					_("{0}: {1} is marked out of {2}").format(students[student], keys[key]["title"], f"{keys[key]['out_of']:g}")
				)
			current.setdefault(student, {})[key] = number
	doc.set(
		"scores",
		[
			{"student": student, "assessment_key": key, "score": results.store(value)}
			for student, given in current.items()
			if student in students
			for key, value in given.items()
			if key in keys and value is not None
		],
	)
	apply(doc)
	results.work_out_sheet(doc)


def out(doc) -> dict:
	return {
		"assessments": [
			{f: a.get(f) for f in ("assessment_key", "title", "kind", "out_of", "weight")} | {"due_date": str(a.due_date) if a.due_date else None}
			for a in doc.get("assessments") or []
		],
		"scores": scores_of(doc),
		"ca_from_gradebook": uses_gradebook(doc),
	}
