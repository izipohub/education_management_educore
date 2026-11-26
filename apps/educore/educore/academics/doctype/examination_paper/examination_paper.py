from frappe.model.document import Document


class ExaminationPaper(Document):
	def validate(self):
		from educore.academics.exam_timetable import validate_paper

		validate_paper(self)
