"""Demo service requests (development only): Anna at Keetmanshoop asks for a letter of enrolment for an embassy (with
the Registry); Ndapewa at Windhoek cannot sign in to Moodle (the ICT office asked her a question, she answered).
Runs from demo_students.create, after the students."""

import frappe
from frappe.utils import add_days, now_datetime, nowdate

from educore.academics import service_requests as sr

REQUESTS = (
	("student1.kmp@educore.localhost", "Letter of enrolment", "For the German embassy, stating that I am registered full-time for 2026 and my expected completion year."),
	("student1.whk@educore.localhost", "IT account", "I cannot sign in to Moodle since Monday; EduCore works."),
)


def create() -> int:
	made = 0
	for user, category, details in REQUESTS:
		student = frappe.db.get_value("Student", {"user": user})
		if not student or not frappe.db.exists("Service Request Category", category):
			continue
		if frappe.db.exists("Service Request", {"student": student, "category": category}):
			continue
		doc = sr.ask(student, category, details)
		made += 1
		if category == "IT account":
			# asked yesterday; ICT wrote, the student answered
			doc.db_set({"submitted_on": add_days(now_datetime(), -1), "due_on": nowdate()})
			doc.reload()
			doc.append("messages", {"posted_by": "Administrator", "posted_by_name": "ICT Service Desk", "from_student": 0, "posted_on": add_days(now_datetime(), -1), "message": "Which browser do you use, and what does Moodle say when you sign in?"})
			doc.append("messages", {"posted_by": user, "posted_by_name": frappe.db.get_value("Student", student, "student_name"), "from_student": 1, "posted_on": now_datetime(), "message": "Chrome on my phone. It says my password is wrong."})
			doc.status = sr.IN_PROGRESS
			doc.save(ignore_permissions=True)
	return made
