"""Demo disciplinary cases (development only): Anna at Keetmanshoop reported by her lecturer for using a phone in a
test (waiting for Student Affairs); Ndapewa at Windhoek given a written warning for disrupting a laboratory session,
which she may still appeal. Runs from demo_students.create, after the students."""

import frappe
from frappe.utils import add_days, nowdate

from educore.academics import discipline as d


def _as(user: str, run):
	previous = frappe.session.user
	frappe.set_user(user)
	try:
		return run()
	finally:
		frappe.set_user(previous)


def create() -> int:
	made = 0
	anna = frappe.db.get_value("Student", {"user": "student1.kmp@educore.localhost"})
	if anna and not frappe.db.exists("Disciplinary Case", {"student": anna}) and frappe.db.exists("User", "lecturer.accf.kmp@educore.localhost"):
		_as("lecturer.accf.kmp@educore.localhost", lambda: d.report(anna, add_days(nowdate(), -2), "Used a phone during Test 2 of FIN2511 after being asked to put it away; the invigilator took the phone until the end of the test."))
		made += 1
	ndapewa = frappe.db.get_value("Student", {"user": "student1.whk@educore.localhost"})
	officer = "student-affairs-officer.whk@educore.localhost"
	if ndapewa and not frappe.db.exists("Disciplinary Case", {"student": ndapewa}) and frappe.db.exists("User", officer):
		reporter = frappe.db.get_value("User", {"name": ("like", "lecturer.comp.whk%")}) or "Administrator"
		case = _as(reporter, lambda: d.report(ndapewa, add_days(nowdate(), -6), "Played loud music and refused to stop during the CMP1511 laboratory session; other students could not work."))

		def decide():
			doc = frappe.get_doc("Disciplinary Case", case.name)
			d.investigate(doc)
			doc.investigation_note = "Spoke to the student and two classmates; she admits it and apologised."
			doc.save(ignore_permissions=True)
			d.decide(doc, d.RESPONSIBLE, d.WRITTEN_WARNING, "A first offence, admitted; a repeat will go to the disciplinary committee.")

		_as(officer, decide)
		made += 1
	return made
