import json

import frappe
from frappe.tests import IntegrationTestCase

from educore_theme import branding

BRANDING_FIELDS = tuple(branding.DEFAULTS)


class TestBranding(IntegrationTestCase):
	def setUp(self):
		self._reset_branding()

	def tearDown(self):
		self._reset_branding()
		branding.apply()

	def _reset_branding(self):
		for field in BRANDING_FIELDS:
			frappe.db.set_single_value("EduCore Branding", field, None)
		branding.clear_cache()

	def _set_branding(self, **values):
		# set directly: saving the form would try to attach these made-up /files paths as File records
		for field, value in values.items():
			frappe.db.set_single_value("EduCore Branding", field, value)
		branding.apply()

	def test_defaults_to_the_educore_brand(self):
		brand = branding.get_branding()
		self.assertEqual(brand["institution_name"], "EduCore")
		self.assertEqual(brand["logo"], branding.DEFAULTS["logo"])
		self.assertEqual(brand["splash"], branding.SPLASH)
		self.assertEqual(len(brand["facts"]), 3)

	def test_puts_the_name_and_logos_in_the_settings(self):
		frappe.db.set_single_value("Website Settings", "app_logo", None)
		frappe.db.set_single_value("Navbar Settings", "app_logo", "/assets/erpnext/images/erpnext-logo.svg")
		frappe.db.set_single_value("System Settings", "app_name", "Frappe")
		branding.apply()
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_logo"), branding.DEFAULTS["logo"])
		self.assertEqual(frappe.db.get_single_value("Website Settings", "favicon"), branding.DEFAULTS["favicon"])
		self.assertEqual(frappe.db.get_single_value("Website Settings", "splash_image"), branding.SPLASH)
		self.assertEqual(frappe.db.get_single_value("Navbar Settings", "app_logo"), branding.DEFAULTS["logo"])
		self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), "EduCore")
		from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo

		self.assertEqual(get_app_logo(), branding.DEFAULTS["logo"])

	def test_a_universitys_branding_replaces_the_defaults(self):
		branding.apply()
		self._set_branding(
			institution_name="University of Example",
			logo="/files/uex-logo.png",
			mark="/files/uex-mark.png",
			accent_color="#7C3AED",
		)
		brand = branding.get_branding()
		self.assertEqual(brand["institution_name"], "University of Example")
		self.assertEqual(brand["splash"], "/files/uex-mark.png")
		self.assertEqual(brand["text_on_accent"], "#FFFFFF")
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_logo"), "/files/uex-logo.png")
		self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), "University of Example")

		# and a later change replaces the university's earlier value, which this app wrote
		self._set_branding(logo="/files/uex-logo-2026.png")
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_logo"), "/files/uex-logo-2026.png")

	def test_leaves_an_administrators_own_logo_alone(self):
		branding.apply()
		frappe.db.set_single_value("Website Settings", "app_logo", "/files/our-own-logo.png")
		branding.apply()
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_logo"), "/files/our-own-logo.png")
		frappe.db.set_single_value("Website Settings", "app_logo", None)

	def test_rejects_a_colour_that_is_not_a_colour_code(self):
		doc = frappe.get_single("EduCore Branding")
		doc.primary_color = "red; background: url(x)"
		self.assertRaises(frappe.ValidationError, doc.save, ignore_permissions=True)

	def test_unsafe_values_never_reach_the_page(self):
		frappe.db.set_single_value("EduCore Branding", "login_background", '/files/x.png");}</style><script>')
		frappe.db.set_single_value("EduCore Branding", "login_text", "</script><script>alert(1)</script>")
		branding.clear_cache()
		context = branding.website_context(frappe._dict())
		head = context["head_html"]
		self.assertIn("--edu-login-image:none;", head)
		self.assertNotIn("</script><script>alert", head)
		config = head.split("window.educore_branding=", 1)[1].rsplit(";</script>", 1)[0]
		self.assertEqual(json.loads(config)["login_text"], "</script><script>alert(1)</script>")

	def test_text_on_the_accent_stays_readable(self):
		self.assertEqual(branding._text_on("#F2B33D"), branding.DARK_TEXT)
		self.assertEqual(branding._text_on("#1E3A8A"), "#FFFFFF")
		self.assertEqual(branding._text_on("#fff"), branding.DARK_TEXT)

	def test_stock_logos_in_the_desk_become_the_brands_icon(self):
		bootinfo = frappe._dict(
			app_data=[
				{"app_name": "erpnext", "app_logo_url": "/assets/erpnext/images/erpnext-logo.svg"},
				{"app_name": "hrms", "app_logo_url": "/assets/hrms/images/frappe-hr-logo.svg"},
				{"app_name": "other", "app_logo_url": ["/assets/frappe/images/frappe-framework-logo.svg"]},
			]
		)
		branding.boot_session(bootinfo)
		mark = branding.DEFAULTS["mark"]
		self.assertEqual(
			[a["app_logo_url"] for a in bootinfo.app_data],
			[mark, "/assets/hrms/images/frappe-hr-logo.svg", mark],
		)
