from frappe.model.document import Document

from educore_theme import branding


class EduCoreBranding(Document):
	def validate(self):
		for field in ("primary_color", "accent_color", "background_color"):
			value = self.get(field)
			if value and not branding.is_hex_colour(value):
				from frappe import _, throw

				throw(_("{0} must be a colour code such as #1E3A8A").format(self.meta.get_label(field)))

	def on_update(self):
		branding.apply()
