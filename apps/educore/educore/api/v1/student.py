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

	today = getdate(nowdate())
	unpaid = [i for i in invoices if flt(i.outstanding_amount) > 0]
	return {
		"billed": round(sum(flt(i.grand_total) for i in invoices), 2),
		"paid": round(sum(flt(p.amount) for p in payments), 2),
		"owing": round(sum(flt(i.outstanding_amount) for i in invoices), 2),
		"overdue": round(sum(flt(i.outstanding_amount) for i in unpaid if getdate(i.due_date) < today), 2),
		"next_due": str(min(getdate(i.due_date) for i in unpaid)) if unpaid else None,
		"invoices": [
			{**i, "posting_date": str(i.posting_date), "due_date": str(i.due_date), "remarks": None} for i in invoices
		],
		"entries": entries,
	}


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
	}
