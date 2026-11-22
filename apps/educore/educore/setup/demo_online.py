"""Online applications for the demo (development only), one per kind of route, made through the applicant API:
Nangula Haufiku (school leaver, BACC at Oshakati) and Ndinelao Shikongo (postgraduate, the MBA) have submitted,
with documents waiting to be checked and the fee not received; Festus Nangolo (mature age entry) has a draft;
Tomas Iipinge (school leaver, BCS at Windhoek) holds a conditional offer awaiting his response.

Called from demo_students.create, after the users exist. Re-running changes nothing once it is there.
"""

import io

import frappe
from frappe.utils import add_days, nowdate

from educore.access.demo_users import DOMAIN, new_user

LOGIN = f"online.applicant@{DOMAIN}"


def demo_pdf(text: str = "DEMO CERTIFIED COPY") -> bytes:
	"""A small valid one-page PDF (Frappe parses uploaded PDFs)"""
	content = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
	objects = [
		b"<< /Type /Catalog /Pages 2 0 R >>",
		b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
		b"/Resources << /Font << /F1 5 0 R >> >> >>",
		b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
		b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
	]
	out, offsets = io.BytesIO(), []
	out.write(b"%PDF-1.4\n")
	for number, body in enumerate(objects, start=1):
		offsets.append(out.tell())
		out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
	xref = out.tell()
	out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
	for offset in offsets:
		out.write(f"{offset:010d} 00000 n \n".encode())
	out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
	return out.getvalue()


#: login: (first name, last name, application, documents, submit); each made through the applicant API
APPLICATIONS = {
	LOGIN: (
		"Nangula",
		"Haufiku",
		{
			"pathway": "School leaver",
			"personal": {"date_of_birth": "2007-11-02", "gender": "Female", "nationality": "Namibian", "city": "Ongwediva"},
			"school": {"centre_number": "DEMO-201"},
			"exam_number": "DEMO-201-0107",
			"exam_year": 2026,
			"results": [
				{"subject": "English Second Language", "level": "NSSCO", "grade": "B"},
				{"subject": "Mathematics", "level": "NSSCO", "grade": "C"},
				{"subject": "Accounting", "level": "NSSCO", "grade": "B"},
				{"subject": "Economics", "level": "NSSCO", "grade": "C"},
				{"subject": "Business Studies", "level": "NSSCO", "grade": "A"},
				{"subject": "Geography", "level": "NSSCO", "grade": "D"},
			],
			"choices": ["BACC-OSH-FT", "DIT-OSH-FT"],
		},
		("National ID or Passport", "Birth Certificate", "NSSC Statement of Results or Certificate"),
		True,
	),
	# postgraduate: a bachelor's with 68%, for the MBA (needs NQF 7 and 60%)
	f"postgrad.applicant@{DOMAIN}": (
		"Ndinelao",
		"Shikongo",
		{
			"pathway": "Postgraduate",
			"personal": {"date_of_birth": "1994-03-15", "gender": "Female", "nationality": "Namibian", "city": "Windhoek"},
			"prior_qualifications": [
				{"qualification": "Bachelor of Accounting", "institution": "EduCore Demo University", "country": "Namibia",
				 "nqf_level": 7, "year_completed": 2016, "average": 68},
			],
			"employment": [
				{"employer": "Demo Mining Ltd", "position": "Financial Accountant", "from_date": "2017-02-01", "duties": "Month-end, audits"},
			],
			"referees": [
				{"full_name": "Dr Demo Referee One", "position": "Senior Lecturer", "institution": "EduCore Demo University", "email": "referee.one@example.com"},
				{"full_name": "Demo Referee Two", "position": "Finance Manager", "institution": "Demo Mining Ltd", "email": "referee.two@example.com"},
			],
			"choices": ["MBA-WHK-PT"],
		},
		("National ID or Passport", "Birth Certificate", "Degree or Diploma Certificate", "Academic Record",
		 "Curriculum Vitae", "Motivation Letter"),
		True,
	),
	# mature age entry, still a draft: school results short of the points, ten years in retail
	f"mature.applicant@{DOMAIN}": (
		"Festus",
		"Nangolo",
		{
			"pathway": "Mature age entry",
			"personal": {"date_of_birth": "1990-07-21", "gender": "Male", "nationality": "Namibian", "city": "Keetmanshoop"},
			"employment": [
				{"employer": "Demo Retail Group", "position": "Store Manager", "from_date": "2016-01-11", "duties": "Staff, stock, cash-up"},
				{"employer": "Demo Supermarket", "position": "Cashier", "from_date": "2009-03-01", "to_date": "2015-12-31"},
			],
			"choices": ["BBA-KMP-PT", "DAF-KMP-FT"],
		},
		("National ID or Passport", "Birth Certificate", "Curriculum Vitae"),
		False,
	),
	# offered a place, with a condition, awaiting their response
	f"offer.applicant@{DOMAIN}": (
		"Tomas",
		"Iipinge",
		{
			"pathway": "School leaver",
			"personal": {"date_of_birth": "2008-01-19", "gender": "Male", "nationality": "Namibian", "city": "Windhoek"},
			"school": {"centre_number": "DEMO-101"},
			"exam_number": "DEMO-101-0233",
			"exam_year": 2026,
			"results": [
				{"subject": "English Second Language", "level": "NSSCO", "grade": "B"},
				{"subject": "Mathematics", "level": "NSSCAS", "grade": "c"},
				{"subject": "Physical Science", "level": "NSSCO", "grade": "B"},
				{"subject": "Computer Studies", "level": "NSSCO", "grade": "A"},
				{"subject": "Geography", "level": "NSSCO", "grade": "C"},
			],
			"choices": ["BCS-WHK-FT", "DIT-WHK-PT"],
		},
		("National ID or Passport", "Birth Certificate", "NSSC Statement of Results or Certificate"),
		"offer",
	),
}


def create() -> list[str]:
	return [name for login, spec in APPLICATIONS.items() if (name := _create(login, *spec))]


def _offer(name: str):
	"""The fee paid by EFT and matched from the bank statement, documents verified by the Admissions Office, and
	a place offered with a condition"""
	from frappe.model.workflow import apply_workflow

	from educore.admissions import fees

	doc = frappe.get_doc("Student Applicant", name)
	bank_line = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"date": frappe.utils.add_days(nowdate(), -3),
			"bank_account": frappe.db.get_single_value("Admission Settings", "fee_bank_account"),
			"company": frappe.db.get_value("Campus", {"is_main_campus": 1}, "company"),
			"deposit": doc.educore_fee_amount,
			"currency": "NAD",
			"description": f"EFT T IIPINGE {name}",
		}
	).insert(ignore_permissions=True)
	bank_line.submit()
	fees.match_bank_transactions()

	doc = frappe.get_doc("Student Applicant", name)
	for row in doc.educore_documents:
		row.status, row.verified_by, row.verified_on = "Verified", "Administrator", frappe.utils.now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.set_value("Student Applicant", name, "educore_offer_conditions", "Final NSSCAS results to be submitted by 31 January 2027.")
	apply_workflow(frappe.get_doc("Student Applicant", name), "Approve")


def _create(login, first_name, last_name, application, documents, submit) -> str | None:
	from unittest.mock import patch

	from werkzeug.datastructures import FileStorage

	from educore.api.v1 import apply

	if frappe.db.exists("Student Applicant", {"educore_applicant_user": login}):
		return None
	if not frappe.db.exists("User", login):
		frappe.flags.in_import = True
		try:
			new_user(email=login, first_name=first_name, last_name=last_name, password="Campus-Demo-2026", positions=["Applicant"])
		finally:
			frappe.flags.in_import = False

	application = {**application, "intake": "2027 Intake"}
	if "school" in application:
		application["school"] = {"name": frappe.db.get_value("Secondary School", application["school"])}
	frappe.set_user(login)
	try:
		apply.save(application)
		for document in documents:
			upload = FileStorage(stream=io.BytesIO(demo_pdf(document.upper())), filename="scan.pdf")
			with patch.object(frappe, "request", frappe._dict(files={"file": upload}), create=True):
				apply.upload_document(document, add_days(nowdate(), -7))
		result = apply.submit(declaration=True) if submit else apply.my_application()
	finally:
		frappe.set_user("Administrator")
	if submit == "offer":
		_offer(result["name"])
	return result["name"]
