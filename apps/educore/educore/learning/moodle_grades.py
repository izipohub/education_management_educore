"""Online assessments in Moodle: the class's graded activities, and their grades brought into the gradebook.

An assessment of an online type (educore.academics.assessment_types) is linked to an activity of the class's Moodle
course (an assignment, a quiz...; the course is made by the sync, educore.learning.moodle). The lecturer then brings
its grades in: each student's grade (found by the student number, the Moodle user's idnumber) is scaled to what the
assessment is marked out of, and shown in the gradebook to check and save. Moodle's grades are evidence: they become
the CA only through the gradebook and the mark sheet's moderation and approval (AGENT.md 2, 6.4).
"""

import frappe
from frappe import _

from educore.learning.moodle import MoodleClient, MoodleError, settings

#: Moodle activities that carry a grade
GRADED = ("assign", "quiz", "workshop", "lesson", "h5pactivity", "lti", "scorm")
LABELS = {"assign": "Assignment", "quiz": "Quiz", "workshop": "Workshop", "lesson": "Lesson", "h5pactivity": "H5P", "lti": "External tool", "scorm": "SCORM package"}


def _client() -> MoodleClient:
	return MoodleClient.from_settings()


def _course_id(group: str) -> int:
	if not settings().moodle_enabled:
		frappe.throw(_("Moodle is not connected yet: ICT connects it on the Integrations screen"))
	course_id = frappe.db.get_value("Student Group", group, "educore_moodle_course_id")
	if not course_id:
		frappe.throw(_("This class is not in Moodle yet: it is added at the next sync"))
	return course_id


def status(group: str | None) -> dict:
	connected = bool(settings().moodle_enabled)
	return {"connected": connected, "in_moodle": bool(connected and group and frappe.db.get_value("Student Group", group, "educore_moodle_course_id"))}


def _call(function: str, **params):
	try:
		return _client().call(function, **params)
	except MoodleError as e:
		frappe.throw(_("Moodle did not answer as expected: {0}").format(e))
	except Exception as e:  # noqa: BLE001 the network, Moodle down
		frappe.throw(_("Moodle could not be reached: {0}").format(e))


def activities(group: str) -> list[dict]:
	"""The graded activities of the class's Moodle course, by section"""
	out = []
	for section in _call("core_course_get_contents", courseid=_course_id(group)) or []:
		for m in section.get("modules") or []:
			if m.get("modname") in GRADED:
				out.append(
					{
						"cmid": m["id"],
						"name": m.get("name"),
						"kind": LABELS.get(m["modname"], m["modname"]),
						"section": section.get("name"),
						"url": m.get("url"),
					}
				)
	return out


def activity(group: str, cmid: int) -> dict:
	found = next((a for a in activities(group) if a["cmid"] == cmid), None)
	if not found:
		frappe.throw(_("That activity is not in the class's Moodle course"))
	return found


def grades(group: str, cmid: int, out_of: float) -> dict:
	"""Each class student's grade for the activity, scaled to what the assessment is marked out of"""
	course_id = _course_id(group)
	students = set(frappe.get_all("Student Group Student", filters={"parent": group, "active": 1}, pluck="student"))
	report = _call("gradereport_user_get_grade_items", courseid=course_id) or {}
	numbers = None
	scores: dict[str, float] = {}
	for user in report.get("usergrades") or []:
		student = user.get("useridnumber")
		if not student:
			if numbers is None:
				numbers = {u["id"]: u.get("idnumber") for u in _call("core_enrol_get_enrolled_users", courseid=course_id) or []}
			student = numbers.get(user.get("userid"))
		if student not in students:
			continue
		item = next((i for i in user.get("gradeitems") or [] if i.get("cmid") == cmid), None)
		if not item or item.get("graderaw") is None or not item.get("grademax"):
			continue
		scores[student] = round(float(item["graderaw"]) / float(item["grademax"]) * float(out_of), 1)
	return {"scores": scores, "not_graded": len(students - set(scores))}
