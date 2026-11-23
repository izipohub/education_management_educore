"""Integrations, for ICT: connecting Moodle (educore.learning.moodle). The token is written, never read back."""

import frappe
from frappe import _

from educore.learning import moodle

ICT_ROLES = ("System Manager",)
FIELDS = ("moodle_enabled", "moodle_url", "sign_in", "campus_categories", "student_role_id", "teacher_role_id")


def _require():
	if not set(frappe.get_roles()) & set(ICT_ROLES):
		frappe.throw(_("Integrations are set up by ICT"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def settings() -> dict:
	_require()
	s = moodle.settings()
	classes = frappe.get_all(
		"Student Group",
		filters={"group_based_on": "Course", "disabled": 0},
		fields=["name", "educore_moodle_course_id", "educore_moodle_synced_on", "educore_moodle_error"],
	)
	return {
		"moodle": {
			**{f: s.get(f) for f in FIELDS},
			"has_token": bool(s.get_password("moodle_token", raise_exception=False)),
			"last_sync_on": str(s.last_sync_on) if s.last_sync_on else None,
			"last_sync_result": s.last_sync_result,
		},
		"classes": {
			"total": len(classes),
			"in_moodle": sum(1 for c in classes if c.educore_moodle_course_id and not c.educore_moodle_error),
			"failed": [{"name": c.name, "error": c.educore_moodle_error} for c in classes if c.educore_moodle_error],
		},
		"sign_in_options": ["Single sign-on", "Moodle password"],
	}


@frappe.whitelist(methods=["POST"])
def save(data: dict | str) -> dict:
	_require()
	data = frappe.parse_json(data)
	s = moodle.settings()
	for field in FIELDS:
		if field in data:
			s.set(field, data[field])
	if data.get("moodle_token"):
		s.moodle_token = data["moodle_token"].strip()
	url = (s.moodle_url or "").strip().rstrip("/")
	if url and not url.startswith("https://") and not frappe.conf.developer_mode:
		frappe.throw(_("Use the Moodle address with https://"))
	s.moodle_url = url or None
	if s.moodle_enabled and not (s.moodle_url and (data.get("moodle_token") or s.get_password("moodle_token", raise_exception=False))):
		frappe.throw(_("Give the Moodle address and web service token before connecting"))
	s.save(ignore_permissions=True)
	return settings()


@frappe.whitelist(methods=["POST"])
def test(url: str | None = None, token: str | None = None) -> dict:
	"""Try the address and token (those typed, or those saved)"""
	_require()
	try:
		return {"ok": True, **moodle.test_connection(url, token)}
	except Exception as e:
		return {"ok": False, "error": str(e)}


@frappe.whitelist(methods=["POST"])
def sync_now() -> dict:
	"""Sync every class now, in the background"""
	_require()
	if not moodle.settings().moodle_enabled:
		frappe.throw(_("Connect Moodle first"))
	frappe.enqueue("educore.learning.moodle.sync_all", queue="long", job_id="educore-moodle-sync", deduplicate=True)
	return {"queued": True}
