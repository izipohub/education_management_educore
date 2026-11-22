import frappe
from frappe import _
from frappe.model.document import Document


class Campus(Document):
	def validate(self):
		self.campus_code = (self.campus_code or "").strip().upper()
		if self.is_main_campus:
			other_main = frappe.db.exists(
				"Campus",
				{"company": self.company, "is_main_campus": 1, "name": ("!=", self.name)},
			)
			if other_main:
				frappe.throw(_("{0} is already the main campus of {1}").format(other_main, self.company))

	def before_insert(self):
		self.ensure_cost_center()
		self.ensure_branch()

	def on_update(self):
		# a campus created before its company had accounts, or whose links were cleared, gets them back
		if not self.cost_center or not self.branch:
			self.ensure_cost_center()
			self.ensure_branch()
			self.db_update()

	def ensure_cost_center(self):
		"""A leaf cost center under the university's root, so campus postings can be reported per campus.
		It becomes a group only if the campus ever needs sub-budgets (AGENT.md 5.1.2)."""
		if self.cost_center and frappe.db.exists("Cost Center", self.cost_center):
			return
		abbr = frappe.get_cached_value("Company", self.company, "abbr")
		name = f"{self.campus_name} - {abbr}"
		if not frappe.db.exists("Cost Center", name):
			root = frappe.db.get_value(
				"Cost Center", {"company": self.company, "is_group": 1, "parent_cost_center": ("in", ("", None))}
			)
			if not root:
				frappe.throw(_("{0} has no root cost center yet; run the university setup first").format(self.company))
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": self.campus_name,
					"parent_cost_center": root,
					"company": self.company,
					"is_group": 0,
				}
			).insert(ignore_permissions=True)
		self.cost_center = name

	def ensure_branch(self):
		if self.branch and frappe.db.exists("Branch", self.branch):
			return
		if not frappe.db.exists("Branch", self.campus_name):
			frappe.get_doc({"doctype": "Branch", "branch": self.campus_name}).insert(ignore_permissions=True)
		self.branch = self.campus_name
