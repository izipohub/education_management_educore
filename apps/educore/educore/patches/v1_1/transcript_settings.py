"""Official transcripts need financial clearance unless the university says otherwise (the setting's default, which
a site made before the setting does not get by itself)."""

import frappe


def execute():
	frappe.db.set_single_value("Registration Settings", "transcript_needs_clearance", 1)
