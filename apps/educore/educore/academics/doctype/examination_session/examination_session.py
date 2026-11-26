from frappe.model.document import Document


class ExaminationSession(Document):
	def validate(self):
		from educore.academics.exam_timetable import validate_session

		validate_session(self)
