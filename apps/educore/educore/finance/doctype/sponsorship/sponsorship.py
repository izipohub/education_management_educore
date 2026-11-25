from frappe.model.document import Document


class Sponsorship(Document):
	def validate(self):
		from educore.finance.sponsors import validate_sponsorship

		validate_sponsorship(self)
