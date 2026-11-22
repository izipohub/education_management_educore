import frappe
from frappe import _
from frappe.model.document import Document

MODE_CODES = {"Full-time": "FT", "Part-time": "PT", "Distance": "DL", "Blended": "BL"}


class ProgrammeOffering(Document):
	def autoname(self):
		# BCS-OSH-FT: programme code, campus code, mode
		programme = frappe.db.get_value("Program", self.program, "educore_programme_code") or self.program
		campus = frappe.db.get_value("Campus", self.campus, "campus_code") or self.campus
		self.name = f"{programme}-{campus}-{MODE_CODES[self.mode_of_study]}"

	def validate(self):
		self.check_duplicate()
		self.check_campus_runs_the_unit()

	def check_duplicate(self):
		filters = {"program": self.program, "campus": self.campus, "mode_of_study": self.mode_of_study}
		# a new offering is already named (autoname runs first), so it must not exclude its own name
		if not self.is_new():
			filters["name"] = ("!=", self.name)
		existing = frappe.db.exists("Programme Offering", filters)
		if existing:
			frappe.throw(_("{0} already offers this programme {1}: {2}").format(self.campus, self.mode_of_study, existing))

	def check_campus_runs_the_unit(self):
		"""A campus offers a programme only if the programme's faculty or department works on that campus"""
		if not self.department:
			return
		campuses = frappe.get_all("Unit Campus", filters={"parent": self.department, "parenttype": "Department"}, pluck="campus")
		if campuses and self.campus not in campuses:
			frappe.throw(
				_("{0} does not work on {1}. Add the campus to the unit first, or offer the programme on: {2}").format(
					self.department, self.campus, ", ".join(campuses)
				)
			)
