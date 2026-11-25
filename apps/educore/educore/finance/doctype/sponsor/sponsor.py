from frappe.model.document import Document


class Sponsor(Document):
	def validate(self):
		from educore.finance.sponsors import validate_sponsor

		validate_sponsor(self)

	def after_insert(self):
		from educore.finance.sponsors import ensure_customer

		ensure_customer(self)
