from frappe.model.document import Document


class InstalmentPlan(Document):
	def validate(self):
		from educore.finance.instalments import validate_plan

		validate_plan(self)
