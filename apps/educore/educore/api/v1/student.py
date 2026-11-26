"""The student portal: a student's own record, programme, courses and fee statement.

Who the student is comes only from the signed-in session (Student.user); no function here takes a student
as a parameter, so no request can ask for another student's data. Records the Student role cannot list
itself (course enrolments, payments) are read here filtered to that student alone.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def _current_student() -> dict:
	student = frappe.db.get_value(
		"Student",
		{"user": frappe.session.user, "enabled": 1},
		["name", "student_name", "student_email_id", "campus", "department", "joining_date"],
		as_dict=True,
	)
	if not student:
		frappe.throw(_("This page is for students."), frappe.PermissionError)
	return student


def _enrolments(student: str) -> list[dict]:
	rows = frappe.get_all(
		"Program Enrollment",
		filters={"student": student, "docstatus": 1},
		fields=[
			"name",
			"program",
			"educore_programme_offering as offering",
			"campus",
			"educore_mode_of_study as mode_of_study",
			"academic_year",
			"enrollment_date",
		],
		order_by="enrollment_date desc",
	)
	for row in rows:
		row["programme_code"], row["qualification"], row["nqf_level"] = frappe.db.get_value(
			"Program", row.program, ["educore_programme_code", "educore_qualification_type", "educore_nqf_level"]
		) or (None, None, None)
		courses = frappe.get_all(
			"Course Enrollment", filters={"program_enrollment": row.name}, pluck="course", order_by="course asc"
		)
		row["courses"] = [
			frappe.db.get_value(
				"Course",
				course,
				["name as course", "educore_course_code as code", "educore_credits as credits", "educore_nqf_level as nqf_level"],
				as_dict=True,
			)
			for course in courses
		]
		row["courses"].sort(key=lambda c: c.code or c.course)
	return rows


def _fee_statement(student: str) -> dict:
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"student": student, "docstatus": 1},
		fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status", "remarks"],
		order_by="posting_date asc, name asc",
	)
	payments = []
	if invoices:
		ref = frappe.qb.DocType("Payment Entry Reference")
		pe = frappe.qb.DocType("Payment Entry")
		payments = (
			frappe.qb.from_(ref)
			.join(pe)
			.on(pe.name == ref.parent)
			.select(pe.name, pe.posting_date, pe.reference_no, ref.reference_name.as_("invoice"), ref.allocated_amount.as_("amount"))
			.where((ref.reference_doctype == "Sales Invoice") & (ref.reference_name.isin([i.name for i in invoices])))
			.where(pe.docstatus == 1)
			.orderby(pe.posting_date)
			.run(as_dict=True)
		)

	# one chronological statement: fees charged (+), payments received (-), running balance
	entries = [
		{
			"date": str(i.posting_date),
			"kind": "invoice",
			"reference": i.name,
			"description": (i.remarks or "").split(". Enrolled by")[0] or _("Fees"),
			"amount": flt(i.grand_total),
		}
		for i in invoices
	] + [
		{
			"date": str(p.posting_date),
			"kind": "payment",
			"reference": p.name,
			"description": _("Payment {0}").format(p.reference_no or "").strip(),
			"amount": -flt(p.amount),
		}
		for p in payments
	]
	entries.sort(key=lambda e: (e["date"], 0 if e["kind"] == "invoice" else 1))
	balance = 0.0
	for entry in entries:
		balance += entry["amount"]
		entry["balance"] = round(balance, 2)

	unpaid = [i for i in invoices if flt(i.outstanding_amount) > 0]
	# overdue and next due follow the instalments (educore.finance.instalments)
	from educore.finance import instalments

	schedule = instalments.due(student)
	return {
		"billed": round(sum(flt(i.grand_total) for i in invoices), 2),
		"paid": round(sum(flt(p.amount) for p in payments), 2),
		"owing": round(sum(flt(i.outstanding_amount) for i in unpaid), 2),
		"overdue": schedule["overdue"],
		"next_due": schedule["next_due"],
		"next_amount": schedule["next_amount"],
		"instalments": schedule["instalments"],
		"invoices": [
			{**i, "posting_date": str(i.posting_date), "due_date": str(i.due_date), "remarks": None} for i in invoices
		],
		"entries": entries,
		# paid and not yet set against an invoice: counts towards the next year's deposit
		"in_advance": _in_advance(student),
		# how to pay: EFT into the university's account, the student number as the reference
		"how_to_pay": {"bank": _bank_details(), "reference": student},
	}


def _in_advance(student: str) -> float:
	from educore.registration.rules import paid_in_advance

	return round(paid_in_advance(student), 2)


def _bank_details() -> dict:
	from educore.admissions.fees import bank_details

	return bank_details()


@frappe.whitelist(methods=["GET"])
def overview() -> dict:
	student = _current_student()
	return {
		"student": {
			"number": student.name,
			"name": student.student_name,
			"email": student.student_email_id,
			"campus": student.campus,
			"faculty": (student.department or "").rsplit(" - ", 1)[0] or None,
			"joining_date": str(student.joining_date) if student.joining_date else None,
		},
		"enrolments": _enrolments(student.name),
		"fees": _fee_statement(student.name),
		# class attendance this year, per class (educore.academics.attendance)
		"attendance": _attendance(student.name),
		# Finance's holds on the student, with the reason
		"holds": _holds(student.name),
		# the overview at the top: today's classes, assessments due soon, examinations ahead
		"ahead": _ahead(student.name),
	}


@frappe.whitelist(methods=["GET"])
def assessments() -> dict:
	"""The student's modules this year: each one's assessments once its plan is approved, and their scores (as marked,
	or once published, as the university decides) (educore.academics.gradebook)"""
	from educore.academics import gradebook

	return gradebook.of_student(_current_student().name)


def _ahead(student: str) -> dict:
	from frappe.utils import add_days

	from educore.academics import attendance, gradebook
	from educore.academics.exam_timetable import of_student as papers_of

	today = nowdate()
	mine = gradebook.of_student(student)
	lessons = []
	for m in mine["modules"]:
		for lesson in attendance.lessons(m["group"], today):
			lessons.append({"code": m["code"], "course": m["course"], **{k: lesson[k] for k in ("start_time", "end_time", "room_name", "kind")}})
	until = str(add_days(today, 21))
	due = [
		{"code": m["code"], "course": m["course"], "title": a["title"], "due_date": a["due_date"], "moodle_url": a["moodle_url"]}
		for m in mine["modules"]
		for a in m["assessments"]
		if a["due_date"] and today <= a["due_date"] <= until and a["score"] is None
	]
	papers = [p for p in papers_of(student) if str(p.get("exam_date")) >= today]
	return {
		"lessons": sorted(lessons, key=lambda l: l["start_time"]),
		"due": sorted(due, key=lambda d: d["due_date"]),
		"papers": sorted(papers, key=lambda p: (str(p.get("exam_date")), str(p.get("start_time"))))[:3],
	}


def _attendance(student: str) -> list[dict]:
	from educore.academics import attendance

	return attendance.of_student(student)


def _holds(student: str) -> list[dict]:
	from educore.finance.clearance import active_holds

	return [{"reason": h.reason, "placed_on": str(h.placed_on)} for h in active_holds(student)]
