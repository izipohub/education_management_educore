"""Completing a programme: whether a student meets the programme's requirements, from published results.

A student is eligible when every required course of the programme's curriculum is passed and the credits passed
on the curriculum reach the programme's total (Program.educore_credits; without one, the required courses alone
decide). The Registrar confirms completion once the Senate (or the board it delegates to) has approved the award:
the Student's completion fields are set, and the academic record becomes final. A standing set by hand (On hold,
Excluded) holds the confirmation back.
"""

import frappe
from frappe import _

from educore.registration import rules

ELIGIBLE, NOT_YET, COMPLETED = "Eligible", "Not yet", "Completed"
#: standings that hold back completion until the registry clears them
HELD = ("On hold", "Excluded")


def latest_programme(student: str) -> dict | None:
	return frappe.db.get_value(
		"Program Enrollment",
		{"student": student, "docstatus": 1},
		["program", "academic_year", "educore_year_of_study as year_of_study"],
		as_dict=True,
		order_by="academic_year desc, enrollment_date desc",
	)


def assess(curriculum: list[dict], results: dict[str, str], needed: int) -> dict:
	"""Where a student stands against a programme: credits passed on its curriculum, the required courses not yet
	passed, and whether that meets the requirements"""
	passed = {course for course, result in results.items() if result == "Pass"}
	credits = sum(c["credits"] for c in curriculum if c["course"] in passed)
	outstanding = [c["course_name"] for c in curriculum if c["required"] and c["course"] not in passed]
	return {
		"credits_passed": credits,
		"credits_needed": needed,
		"outstanding": outstanding,
		"meets": not outstanding and credits >= needed,
	}


def progress(student: str) -> dict:
	"""One student's progress towards completing their programme"""
	doc = frappe.db.get_value(
		"Student",
		student,
		["name", "student_name", "campus", "educore_academic_standing as standing", "educore_completed_on as completed_on",
		 "educore_completed_programme as completed_programme", "educore_completion_reference as reference"],
		as_dict=True,
	)
	enrolment = latest_programme(student) or {}
	program = doc.completed_programme or enrolment.get("program")
	out = {
		**doc,
		"completed_on": str(doc.completed_on) if doc.completed_on else None,
		"program": program,
		"year_of_study": enrolment.get("year_of_study"),
		"held": doc.standing if doc.standing in HELD else None,
	}
	if not program:
		return {**out, "status": NOT_YET, "credits_passed": 0, "credits_needed": 0, "outstanding": []}
	needed = frappe.get_cached_value("Program", program, "educore_credits") or 0
	out.update(assess(rules.curriculum(program), rules.results_by_course(student), needed))
	out["status"] = COMPLETED if doc.completed_on else ELIGIBLE if out.pop("meets") else NOT_YET
	# financial clearance, which graduation needs where the university requires it (educore.finance.clearance)
	if out["status"] == ELIGIBLE:
		from educore.finance import clearance

		state = clearance.status(student)
		out["clearance"] = {"cleared": state["cleared"], "reasons": state["reasons"], "needed": clearance.graduation_needs_clearance()}
	return out


def confirm(student: str, reference: str, completed_on: str):
	"""Record the completion the Senate approved. Only an eligible student, not held back."""
	state = progress(student)
	if state["status"] == COMPLETED:
		frappe.throw(_("{0} has completed {1} already").format(state["student_name"], state["program"]))
	if state["status"] != ELIGIBLE:
		frappe.throw(_("{0} does not yet meet the requirements of {1}").format(state["student_name"], state["program"]))
	if state["held"]:
		frappe.throw(_("{0} is {1}: clear that first").format(state["student_name"], state["held"].lower()))
	from educore.finance.clearance import require_for_graduation

	require_for_graduation(student, state["student_name"])
	frappe.db.set_value(
		"Student",
		student,
		{"educore_completed_on": completed_on, "educore_completed_programme": state["program"], "educore_completion_reference": reference},
	)
	from educore.academics import notify

	notify.send(
		student, "programme_completed", frappe.get_doc("Student", student),
		programme=state["program"], reference=reference, completed_on=notify.date(completed_on),
	)
