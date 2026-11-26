"""The gradebook: a module's continuous assessments and each student's scores, from which the CA mark is worked out.

The lecturer decides the module's assessments (two tests and two assignments, two quizzes, a project...): each is
marked out of what the lecturer chooses and carries a share of the CA, the shares adding up to 100%. A student's CA
mark is the weighted sum of their scores, once every assessment is scored (a missed assessment is scored 0); it then
goes into the mark sheet like a CA typed in (educore.academics.results), and the final mark is worked out with the
examination as before. A module without assessments keeps its CA typed in directly.

Each assessment is of one of the faculty's assessment types, within the share the faculty allows for the type
(educore.academics.assessment_types). An online one is linked to its Moodle activity, and its scores can be brought in
from Moodle for the lecturer to check and save (educore.learning.moodle_grades): evidence, moderated with the rest.

The plan is approved above the lecturer: the lecturer proposes it, the Head of Department (or the Dean) approves it
or returns it with the reason, and scores are entered once it is approved. An approved plan is locked; a change is
made by returning it to the lecturer and approving it again (the scores of the assessments kept stay).

The gradebook belongs to the mark sheet: it can be changed while the marks are with the lecturer, and is locked when
they are submitted.
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from educore.academics import assessment_types, results

PROPOSED, APPROVED = "Proposed", "Approved"
MOODLE_FIELDS = ("moodle_cmid", "moodle_activity", "moodle_url")


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


def _plan(rows) -> list[tuple]:
	return [(r.get("assessment_key"), (r.get("title") or "").strip(), r.get("kind"), flt(r.get("out_of")), flt(r.get("weight"))) for r in rows]


def save(doc, assessments: list[dict], scores: dict[str, dict]):
	"""The lecturer's assessments (kept by key, new ones keyed) and the scores given (student: key: score)"""
	validate_plan(assessments)
	before = {a.assessment_key: a for a in doc.get("assessments") or []}
	if doc.get("plan_status") and _plan(assessments) != _plan(before.values()):
		frappe.throw(
			_("The assessment plan is with the Head of Department")
			if doc.plan_status == PROPOSED
			else _("The assessment plan is approved; the Head of Department returns it if it needs changing")
		)
	assessment_types.check_plan(doc.course, assessments, kept={a.kind for a in before.values()})
	keep = []
	for a in assessments:
		key = a.get("assessment_key") or frappe.generate_hash(length=8)
		row = {
			"assessment_key": key,
			"title": a["title"].strip(),
			"kind": a["kind"],
			"out_of": flt(a["out_of"]),
			"weight": flt(a["weight"]),
			"due_date": a.get("due_date") or None,
		}
		cmid = frappe.utils.cint(a.get("moodle_cmid")) or None
		if cmid:
			old = before.get(key)
			if not old or old.moodle_cmid != cmid:
				from educore.learning import moodle_grades

				activity = moodle_grades.activity(doc.student_group, cmid)
				row.update({"moodle_cmid": cmid, "moodle_activity": activity["name"], "moodle_url": activity["url"]})
			else:
				row.update({f: old.get(f) for f in MOODLE_FIELDS})
		keep.append(row)
	doc.set("assessments", keep)
	keys = {a["assessment_key"]: a for a in keep}
	students = {e.student: e.student_name for e in doc.entries}
	current = scores_of(doc)
	stored = {s: dict(v) for s, v in current.items()}
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
			if number != stored.get(student, {}).get(key) and doc.get("plan_status") != APPROVED:
				frappe.throw(_("Scores are entered once the Head of Department approves the assessment plan"))
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


def propose(doc):
	"""The lecturer's plan to the Head of Department"""
	if doc.get("plan_status"):
		frappe.throw(_("The assessment plan is already with the Head of Department"))
	if not doc.get("assessments"):
		frappe.throw(_("Set up the assessments first"))
	validate_plan([a.as_dict() for a in doc.assessments])
	doc.update({"plan_status": PROPOSED, "plan_note": None})


def approve(doc):
	if doc.get("plan_status") != PROPOSED:
		frappe.throw(_("No assessment plan to approve"))
	doc.update({"plan_status": APPROVED, "plan_approved_by": frappe.session.user, "plan_approved_on": now_datetime(), "plan_note": None})


def return_plan(doc, note: str):
	"""Back to the lecturer, with the reason: a plan to change, or an approved one to change (its scores kept)"""
	if not doc.get("plan_status"):
		frappe.throw(_("The assessment plan is with the lecturer"))
	if not (note or "").strip():
		frappe.throw(_("Say why the plan is returned"))
	doc.update({"plan_status": None, "plan_note": note.strip(), "plan_approved_by": None, "plan_approved_on": None})


def out(doc) -> dict:
	from educore.learning import moodle_grades

	faculty = assessment_types.faculty_of_course(doc.course) if doc else None
	return {
		"assessments": [
			{f: a.get(f) for f in ("assessment_key", "title", "kind", "out_of", "weight", *MOODLE_FIELDS)} | {"due_date": str(a.due_date) if a.due_date else None}
			for a in doc.get("assessments") or []
		],
		"scores": scores_of(doc),
		"ca_from_gradebook": uses_gradebook(doc),
		"plan": {
			"status": doc.get("plan_status") or None,
			"note": doc.get("plan_note"),
			"approved_by": frappe.utils.get_fullname(doc.plan_approved_by) if doc.get("plan_approved_by") else None,
			"approved_on": str(doc.plan_approved_on) if doc.get("plan_approved_on") else None,
		},
		# the faculty's types the lecturer chooses from (with any no longer in use that the plan still has)
		"assessment_types": [
			{"type_name": t.type_name, "online": t.online, "max_share": t.max_share}
			for t in assessment_types.of_faculty(faculty, include_disabled=True)
			if not t.disabled or t.type_name in {a.kind for a in doc.get("assessments") or []}
		],
		"moodle": moodle_grades.status(doc.student_group),
	}
