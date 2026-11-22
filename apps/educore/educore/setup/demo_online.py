"""A submitted online application for the demo (development only): Nangula Haufiku applies for BACC at Oshakati
through the applicant API, with her documents waiting to be checked and the fee not received yet.

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


def create():
	from unittest.mock import patch

	from werkzeug.datastructures import FileStorage

	from educore.api.v1 import apply

	if frappe.db.exists("Student Applicant", {"educore_applicant_user": LOGIN}):
		return None
	if not frappe.db.exists("User", LOGIN):
		frappe.flags.in_import = True
		try:
			new_user(email=LOGIN, first_name="Nangula", last_name="Haufiku", password="Campus-Demo-2026", positions=["Applicant"])
		finally:
			frappe.flags.in_import = False

	frappe.set_user(LOGIN)
	try:
		apply.save(
			{
				"intake": "2027 Intake",
				"personal": {"date_of_birth": "2007-11-02", "gender": "Female", "nationality": "Namibian", "city": "Ongwediva"},
				"school": {"name": frappe.db.get_value("Secondary School", {"centre_number": "DEMO-201"})},
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
			}
		)
		for document in ("National ID or Passport", "Birth Certificate", "NSSC Statement of Results or Certificate"):
			upload = FileStorage(stream=io.BytesIO(demo_pdf(document.upper())), filename="scan.pdf")
			with patch.object(frappe, "request", frappe._dict(files={"file": upload}), create=True):
				apply.upload_document(document, add_days(nowdate(), -7))
		name = apply.submit(declaration=True)["name"]
	finally:
		frappe.set_user("Administrator")
	return name
