from frappe.model.document import Document


class TimetableSlot(Document):
	def validate(self):
		from educore.academics.timetable import validate_slot

		validate_slot(self)
