"""Demo results for EduCore Demo University (development only): the 2026 classes' marks, as the year closes.

The first-year courses' classes are published (entered by the lecturer, moderated by the head of department,
approved by the faculty examination board); Computer Systems at Windhoek waits for moderation and Databases at Windhoek for its lecturer's
marks, so each office has work to see. Marks are steady per student and course; one student writes a supplementary
and one was absent, and the demo students' standing stays good. Re-running adds whatever is missing.
"""

import hashlib

import frappe
from frappe.utils import add_days, get_datetime, nowdate

from educore.academics import results

YEAR = "2026"
WAITING_FOR_MODERATION = "CMP1521 WHK 2026"
NOT_STARTED = "CMP2521 WHK 2026"
BOARD = "Faculty Examination Board, 18-11-2026"
#: class: the student who writes a supplementary examination (CA 50, examination 42: a final mark of 46)
SUPPLEMENTARY = {"CMP1521 OSH 2026": "student1.osh@educore.localhost"}
#: class: the student absent from the examination (a special examination is the examinations office's to grant)
ABSENT = {"EDU1521 OSH 2026": "student2.osh@educore.localhost"}


def _mark(student: str, course: str, salt: str, low: int, high: int) -> int:
	digest = int(hashlib.sha256(f"{student}|{course}|{salt}".encode()).hexdigest(), 16)
	return low + digest % (high - low + 1)


def _curriculum_year(course: str) -> int:
	years = frappe.get_all("Program Course", filters={"course": course, "parenttype": "Program"}, pluck="educore_year")
	return min((y for y in years if y), default=1)


def _lecturer_user(group) -> str | None:
	for row in group.instructors:
		employee = frappe.db.get_value("Instructor", row.instructor, "employee")
		user = frappe.db.get_value("Employee", employee, "user_id") if employee else None
		if user:
			return user
	return None


#: course: the course to pass first, as a yearbook lists them
PREREQUISITES = {
	"Data Structures and Algorithms": "Programming Fundamentals",
	"Databases": "Programming Fundamentals",
	"Linear Algebra": "Calculus I",
	"Corporate Finance": "Financial Accounting I",
	"Organisational Behaviour": "Principles of Management",
	"Community Health Nursing": "Fundamentals of Nursing",
	"Curriculum and Instruction": "Foundations of Education",
}


def _prerequisites():
	for course, first in PREREQUISITES.items():
		if not (frappe.db.exists("Course", course) and frappe.db.exists("Course", first)):
			continue
		doc = frappe.get_doc("Course", course)
		if not doc.get("educore_prerequisites"):
			doc.append("educore_prerequisites", {"prerequisite": first})
			doc.save(ignore_permissions=True)


def create() -> int:
	from educore.setup.demo_registration import set_curriculum

	results.ensure_defaults()
	# each course's year of study first: only first-year courses get 2026 results (a fresh site has no curriculum yet)
	set_curriculum()
	_prerequisites()
	made, published = 0, []
	when = get_datetime(add_days(nowdate(), -6))
	for name in frappe.get_all("Student Group", filters={"group_based_on": "Course", "academic_year": YEAR}, pluck="name"):
		if name == NOT_STARTED or frappe.db.exists("Mark Sheet", name):
			continue
		group = frappe.get_doc("Student Group", name)
		# the 2026 students were in their first year: results for first-year courses only (their year-two courses
		# are registered for 2027)
		if _curriculum_year(group.course) > 1:
			continue
		sheet = frappe.get_doc(
			{
				"doctype": "Mark Sheet",
				"student_group": name,
				"course": group.course,
				"campus": group.get("campus"),
				"academic_year": YEAR,
				"entries": [
					{
						"student": s.student,
						"student_name": s.student_name,
						"ca_mark": _mark(s.student, group.course, "ca", 55, 85),
						"exam_mark": _mark(s.student, group.course, "exam", 50, 82),
					}
					for s in group.students
					if s.active
				],
			}
		)
		supp_user, absent_user = SUPPLEMENTARY.get(name), ABSENT.get(name)
		for entry in sheet.entries:
			user = frappe.db.get_value("Student", entry.student, "user")
			if supp_user and user == supp_user:
				entry.ca_mark, entry.exam_mark = 50, 42
			if absent_user and user == absent_user:
				entry.exam_mark, entry.absent = None, 1
		results.work_out_sheet(sheet)
		if supp_user or absent_user:
			sheet.supp_status = "Open"
		sheet.update({"status": "Submitted", "submitted_by": _lecturer_user(group), "submitted_on": when})
		if name != WAITING_FOR_MODERATION:
			sheet.update(
				{
					"status": "Published",
					"moderated_by": "head-of-department@educore.localhost",
					"moderated_on": add_days(when, 1),
					"approved_by": "examinations-officer@educore.localhost",
					"approved_on": add_days(when, 3),
					"board_reference": BOARD,
					"published_on": add_days(when, 4),
				}
			)
			published += [e.student for e in sheet.entries]
		sheet.insert(ignore_permissions=True)
		made += 1
	if published:
		results.update_standing(published, YEAR)
	return made
