"""The university's brand on an EduCore site.

EduCore ships with its own brand (DEFAULTS). Each installation can override the name, logos, colours and
login page text in the EduCore Branding settings; an empty field keeps the EduCore default.

- apply() puts the name and logos into Website, Navbar and System Settings, on install, on every migrate
  and whenever EduCore Branding is saved. A setting an administrator changed to something of their own
  is left alone; only empty ones, Frappe's or ERPNext's stock values, or values this app wrote earlier
  are (re)written, so running it again is safe.
- website_context() adds the colours (as CSS variables) and the login page text to every website page.
- boot_session() shows the brand's icon in the desk in place of Frappe's and ERPNext's logos.
"""

import json
import re

import frappe

IMAGES = "/assets/educore_theme/images"

DEFAULTS = {
	"institution_name": "EduCore",
	"login_subtitle": "University Management",
	"logo": f"{IMAGES}/educore-logo.svg",
	"logo_on_dark": f"{IMAGES}/educore-logo-white.svg",
	"mark": f"{IMAGES}/educore-mark-192.png",
	"favicon": f"{IMAGES}/favicon.ico",
	"primary_color": "#1E3A8A",
	"accent_color": "#F2B33D",
	"background_color": "#07142B",
	"login_heading": "One university,",
	"login_heading_accent": "every campus connected.",
	"login_text": (
		"Admissions, academic records, examinations, finance, HR and campus operations "
		"for every campus of the university, in one place."
	),
	"login_facts": (
		"Students · Academics | From admission to graduation\n"
		"Finance · HR | Fees, payroll and staff\n"
		"Every campus | One connected university"
	),
	"login_background": "",
}
SPLASH = f"{IMAGES}/educore-mark-512.png"
COLOUR_FIELDS = ("primary_color", "accent_color", "background_color")
IMAGE_FIELDS = ("logo", "logo_on_dark", "mark", "favicon", "login_background")

#: Logos and names that are the stock ones, not an administrator's choice
STOCK_LOGOS = (
	"/assets/erpnext/images/erpnext-logo.svg",
	"/assets/frappe/images/frappe-framework-logo.svg",
	"/assets/frappe/images/frappe-framework-logo.png",
	"/assets/frappe/images/frappe-logo.png",
)
STOCK_NAMES = ("Frappe", "ERPNext", "Frappe HR")

CACHE_KEY = "educore_theme:branding"
#: What apply() last wrote to each setting, so it can tell its own earlier values from an administrator's
APPLIED_KEY = "educore_theme_applied"

DARK_TEXT = "#0B1F3A"


def is_hex_colour(value) -> bool:
	return bool(re.fullmatch(r"#(?:[0-9a-fA-F]{3}){1,2}", (value or "").strip()))


def _safe_path(value) -> str:
	"""A site-relative file path (/files/…, /assets/…) or nothing: the value goes into CSS and HTML"""
	value = (value or "").strip()
	return value if re.fullmatch(r"/[\w./%-]+", value) else ""


def _text_on(colour: str) -> str:
	"""White or dark text, whichever reads better on the colour (WCAG relative luminance)"""
	hex_ = colour.lstrip("#")
	if len(hex_) == 3:
		hex_ = "".join(c * 2 for c in hex_)
	channels = []
	for i in (0, 2, 4):
		c = int(hex_[i : i + 2], 16) / 255
		channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
	luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
	# contrast with white is 1.05 / (L + 0.05); with DARK_TEXT (L ≈ 0.014) it is (L + 0.05) / 0.064
	return "#FFFFFF" if 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.064 else DARK_TEXT


def _parse_facts(text: str) -> list[list[str]]:
	facts = []
	for line in (text or "").splitlines():
		title, _, caption = line.partition("|")
		if title.strip():
			facts.append([title.strip(), caption.strip()])
	return facts[:3]


def get_branding() -> dict:
	"""The brand in effect: EduCore Branding's values, with EduCore's defaults for anything empty"""
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached:
		return cached

	values = dict(DEFAULTS)
	try:
		doc = frappe.get_single("EduCore Branding")
	except frappe.DoesNotExistError:
		doc = None
	if doc:
		for field in DEFAULTS:
			value = (doc.get(field) or "").strip()
			if value:
				values[field] = value

	for field in COLOUR_FIELDS:
		if not is_hex_colour(values[field]):
			values[field] = DEFAULTS[field]
	for field in IMAGE_FIELDS:
		values[field] = _safe_path(values[field]) or DEFAULTS[field]

	values["splash"] = SPLASH if values["mark"] == DEFAULTS["mark"] else values["mark"]
	values["text_on_accent"] = _text_on(values["accent_color"])
	values["facts"] = _parse_facts(values["login_facts"])

	frappe.cache.set_value(CACHE_KEY, values)
	return values


def clear_cache():
	frappe.cache.delete_value(CACHE_KEY)


def _replaceable(current, previously_applied) -> bool:
	current = current or ""
	return (
		not current
		or current in STOCK_LOGOS
		or current in STOCK_NAMES
		or current.startswith(IMAGES)
		or current == previously_applied
	)


def apply():
	"""Puts the brand's name and logos in the site's settings (after install, every migrate and on save)"""
	clear_cache()
	brand = get_branding()
	applied = json.loads(frappe.db.get_default(APPLIED_KEY) or "{}")

	targets = {
		"Website Settings": {
			"app_name": brand["institution_name"],
			"app_logo": brand["logo"],
			"favicon": brand["favicon"],
			"splash_image": brand["splash"],
		},
		"Navbar Settings": {"app_logo": brand["logo"]},
		"System Settings": {"app_name": brand["institution_name"]},
	}
	for doctype, fields in targets.items():
		meta = frappe.get_meta(doctype)
		for field, value in fields.items():
			if not meta.has_field(field):
				continue
			key = f"{doctype}.{field}"
			current = frappe.db.get_single_value(doctype, field)
			if current == value:
				applied[key] = value
			elif _replaceable(current, applied.get(key)):
				frappe.db.set_single_value(doctype, field, value)
				applied[key] = value

	frappe.db.set_default(APPLIED_KEY, json.dumps(applied))
	frappe.clear_cache()


def website_context(context):
	"""Every website page (login, forgot password, /apps): the brand's colours, icons and login text"""
	brand = get_branding()
	image = f'url("{brand["login_background"]}")' if brand["login_background"] else "none"
	# html:root outranks the stylesheet's :root defaults, which the page loads after this <style>
	style = (
		'<style id="educore-branding">html:root{'
		f"--edu-primary:{brand['primary_color']};"
		f"--edu-accent:{brand['accent_color']};"
		f"--edu-night:{brand['background_color']};"
		f"--edu-on-accent:{brand['text_on_accent']};"
		f"--edu-login-image:{image};"
		"}</style>"
	)
	config = {
		key: brand[key]
		for key in (
			"institution_name",
			"login_subtitle",
			"logo_on_dark",
			"mark",
			"login_heading",
			"login_heading_accent",
			"login_text",
			"facts",
		)
	}
	# "</" escaped so no value can close the script element
	script = "<script>window.educore_branding=" + json.dumps(config).replace("</", "<\\/") + ";</script>"
	# head_html, not head_include: every page prints head_html (templates/includes/head.html), while the
	# login page replaces the head_include block with its own. Website Settings' own Head HTML is kept.
	return {
		"head_html": (context.get("head_html") or "") + style + script,
		"favicon": brand["favicon"],
		"splash_image": brand["splash"],
	}


def boot_session(bootinfo):
	"""In the desk, ERPNext (and any app showing Frappe's or ERPNext's stock logo) shows the brand's icon"""
	mark = get_branding()["mark"]
	for app in bootinfo.get("app_data") or []:
		logo = app.get("app_logo_url")
		if isinstance(logo, list):
			logo = logo[0] if logo else None
		if not logo or logo in STOCK_LOGOS:
			app["app_logo_url"] = mark
