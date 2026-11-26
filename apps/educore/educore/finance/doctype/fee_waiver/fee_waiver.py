from frappe.model.document import Document


class FeeWaiver(Document):
	def validate(self):
		from educore.finance.waivers import validate_waiver

		validate_waiver(self)
