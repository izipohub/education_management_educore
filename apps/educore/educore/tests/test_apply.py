import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, nowdate
from werkzeug.datastructures import FileStorage

from educore.access.demo_users import new_user
from educore.api.v1 import admissions, apply

PASSWORD = "Campus-Demo-2026"
GOOD_RESULTS = [
	{"subject": "English Second Language", "level": "NSSCO", "grade": "C"},
	{"subject": "Mathematics", "level": "NSSCO", "grade": "B"},
	{"subject": "Physical Science", "level": "NSSCO", "grade": "C"},
	{"subject": "Biology", "level": "NSSCO", "grade": "D"},
	{"subject": "Geography", "level": "NSSCO", "grade": "B"},
	{"subject": "Oshindonga First Language", "level": "NSSCO", "grade": "A"},
]
PERSONAL = {"date_of_birth": "2008-03-14", "gender": "Female", "nationality": "Namibian"}


def _pdf() -> bytes:
	"""A small, valid PDF (Frappe parses uploaded PDFs)"""
	objects = [
		"<< /Type /Catalog /Pages 2 0 R >>",
		"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>",
	]
	out, offsets = io.BytesIO(), []
	out.write(b"%PDF-1.4\n")
	for i, body in enumerate(objects, start=1):
		offsets.append(out.tell())
		out.write(f"{i} 0 obj\n{body}\nendobj\n".encode())
	xref = out.tell()
	out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
	for offset in offsets:
		out.write(f"{offset:010d} 00000 n \n".encode())
	out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
	return out.getvalue()


class TestOnlineApplication(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Admission", "2027 Intake"):
			self.skipTest("run educore.setup.demo.create_demo_university first")
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")

	def _applicant(self, login):
		email = f"{login}@example.com"
		if not frappe.db.exists("User", email):
			frappe.flags.in_import = True
			try:
				new_user(email=email, first_name="Test", last_name=login.title(), password=PASSWORD, positions=["Applicant"])
			finally:
				frappe.flags.in_import = False
		frappe.set_user(email)
		return email

	def _login(self):
		"""Each test its own applicant: Frappe rolls back once per class, so one test's submitted
		application would otherwise still be there for the next"""
		return "apply." + self._testMethodName.removeprefix("test_")[:40].replace("_", ".").strip(".")

	def _draft(self, login=None, results=GOOD_RESULTS, choices=("BCS-OSH-FT", "BNS-WHK-FT", "DIT-OSH-FT")):
		self._applicant(login or self._login())
		return apply.save(
			{
				"intake": "2027 Intake",
				"personal": PERSONAL,
				"school": {"name": frappe.db.get_value("Secondary School", {"centre_number": "DEMO-201"})},
				"results": list(results),
				"choices": list(choices),
			}
		)

	def _upload(self, document, certified_on=None, filename="scan.pdf", content=None):
		upload = FileStorage(stream=io.BytesIO(content if content is not None else _pdf()), filename=filename)
		with patch.object(frappe, "request", frappe._dict(files={"file": upload}), create=True):
			return apply.upload_document(document, certified_on or add_days(nowdate(), -10))

	def _complete(self, login=None):
		self._draft(login)
		for document in ("National ID or Passport", "Birth Certificate", "NSSC Statement of Results or Certificate"):
			data = self._upload(document)
		return data

	# --- points and eligibility ------------------------------------------------------------------------

	def test_points_are_the_best_five_results_and_each_choice_is_assessed(self):
		data = self._draft()
		# A 7 + B 6 + B 6 + C 5 + C 5 on the placeholder scale
		self.assertEqual(data["points"], 29)
		eligibility = {c["offering"]: (c["eligibility"], c["eligibility_note"]) for c in data["choices"]}
		self.assertEqual(eligibility["BCS-OSH-FT"][0], "Meets requirements")
		self.assertEqual(eligibility["BNS-WHK-FT"], ("Does not meet requirements", "Biology below NSSCO C"))

	def test_english_second_language_counts_as_english(self):
		results = [r for r in GOOD_RESULTS if not r["subject"].startswith("English")]
		data = self._draft(results=results)
		self.assertIn("No result in English", data["choices"][0]["eligibility_note"])
		self.assertEqual(self._draft(results=GOOD_RESULTS)["choices"][0]["eligibility"], "Meets requirements")

	def test_at_most_three_different_choices(self):
		self.assertRaises(frappe.ValidationError, self._draft, choices=("BCS-OSH-FT", "BNS-WHK-FT", "DIT-OSH-FT", "BACC-OSH-FT"))
		self.assertRaises(frappe.ValidationError, self._draft, choices=("BCS-OSH-FT", "BCS-OSH-FT"))

	def test_points_cannot_be_typed_in(self):
		self._draft()
		name = apply.my_application()["name"]
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Student Applicant", name)
		doc.educore_points = 99
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Student Applicant", name, "educore_points"), 29)

	# --- documents -------------------------------------------------------------------------------------

	def test_documents_are_private_and_only_pdf_or_images(self):
		self._draft()
		data = self._upload("National ID or Passport")
		row = next(d for d in data["documents"] if d["document_type"] == "National ID or Passport")
		self.assertEqual(row["status"], "Pending")
		self.assertTrue(row["file_url"].startswith("/private/files/"))
		self.assertRaises(frappe.ValidationError, self._upload, "Birth Certificate", filename="tool.exe", content=b"MZ")
		self.assertRaises(frappe.ValidationError, self._upload, "Birth Certificate", content=b"%PDF-1.4 not really")

	def test_removing_a_document_leaves_an_identical_upload_alone(self):
		# Frappe stores identical files once: the two uploads share a URL but are separate File records
		self._draft()
		self._upload("National ID or Passport")
		data = self._upload("Birth Certificate")
		rows = {d["document_type"]: d for d in data["documents"]}
		self.assertEqual(rows["National ID or Passport"]["file_url"], rows["Birth Certificate"]["file_url"])
		data = apply.remove_document("Birth Certificate")
		kept = next(d for d in data["documents"] if d["document_type"] == "National ID or Passport")
		self.assertTrue(kept["uploaded"])
		name = apply.my_application()["name"]
		frappe.set_user("Administrator")
		file_doc = frappe.db.get_value(
			"Applicant Document", {"parent": name, "document_type": "National ID or Passport"}, "file_doc"
		)
		self.assertTrue(frappe.db.exists("File", file_doc))

	def test_an_old_certification_keeps_the_application_incomplete(self):
		self._complete()
		self._upload("Birth Certificate", certified_on=add_months(nowdate(), -6))
		self.assertTrue(any("Birth Certificate" in gap for gap in apply.my_application()["missing"]))

	# --- submitting ------------------------------------------------------------------------------------

	def test_an_incomplete_application_is_not_submitted(self):
		self._draft()
		self.assertRaises(frappe.ValidationError, apply.submit, declaration=True)
		self.assertEqual(apply.my_application()["status"], "Draft")

	def test_a_complete_application_is_submitted_and_reaches_the_campus_queue(self):
		data = self._complete()
		self.assertEqual(data["missing"], [])
		self.assertRaises(frappe.ValidationError, apply.submit, declaration=False)
		data = apply.submit(declaration=True)
		self.assertEqual((data["status"], data["editable"]), ("Applied", False))
		self.assertRaises(frappe.ValidationError, apply.save, {"personal": {"city": "Elsewhere"}})

		frappe.set_user("admissions-officer.osh@educore.localhost")
		queue = admissions.applications(status="Applied", academic_year="2027")["rows"]
		self.assertIn(data["name"], [row["name"] for row in queue])

	def test_an_applicant_sees_only_their_own_application(self):
		mine = self._draft(self._login() + ".one")["name"]
		self._applicant(self._login() + ".two")
		self.assertIsNone(apply.my_application())
		self.assertNotEqual(self._draft(self._login() + ".two")["name"], mine)

	def test_staff_cannot_use_the_applicant_api(self):
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, apply.my_application)

	# --- registering -----------------------------------------------------------------------------------

	def test_registering_makes_an_applicant_login_once(self):
		frappe.set_user("Guest")
		frappe.flags.in_import = True  # the per-hour user throttle, as for the seeded users
		try:
			with patch("frappe.rate_limiter.rate_limit", lambda *a, **k: (lambda f: f)):
				apply.register.__wrapped__("New", "Applicant", "new.applicant@example.com", "Very-Long-Passphrase-2027")
		finally:
			frappe.flags.in_import = False
		frappe.set_user("Administrator")
		self.assertIn("Applicant", frappe.get_roles("new.applicant@example.com"))
		self.assertEqual(frappe.db.get_value("User", "new.applicant@example.com", "user_type"), "Website User")
		frappe.set_user("Guest")
		self.assertRaises(
			frappe.ValidationError, apply.register.__wrapped__, "New", "Applicant", "new.applicant@example.com", "Another-Passphrase-1"
		)
