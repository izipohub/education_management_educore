"""EduCore's Frappe Workflows, created after install and every migrate and kept as defined here.

Admission decisions run on Student Applicant's own application_status field, so Education's screens,
reports and its "Enroll" step (which sets Admitted) keep working. Who may act comes from the transitions
below; campus User Permissions limit which applicants each officer can open at all. Frappe records every
action on the applicant's timeline, and does not let a user approve an application they created.
"""

import frappe

ADMISSION_WORKFLOW = "EduCore Admission Decision"

#: Workflow State: indicator style
STATES = {"Draft": "", "Applied": "Primary", "Approved": "Success", "Rejected": "Danger", "Admitted": "Info"}
ACTIONS = ("Submit", "Approve", "Reject", "Withdraw Offer", "Reconsider")

#: (state, role that may edit the application in that state). The first is where every application starts.
DOCUMENT_STATES = (
	# the applicant fills it in online (through educore.api.v1.apply), or staff capture a paper application
	("Draft", "Academics User"),
	("Applied", "Academics User"),
	("Approved", "Academics User"),
	("Rejected", "Registrar"),
	# set by Education's enroll step, not by an action
	("Admitted", "Registrar"),
)

#: (from, action, to, roles, the creator may act on their own application)
TRANSITIONS = (
	# the applicant submits their own application: "self-approval" is the point here
	("Draft", "Submit", "Applied", ("Applicant", "Admissions Officer", "Registrar"), True),
	("Applied", "Approve", "Approved", ("Admissions Officer", "Registrar"), False),
	("Applied", "Reject", "Rejected", ("Admissions Officer", "Registrar"), False),
	("Approved", "Withdraw Offer", "Rejected", ("Admissions Officer", "Registrar"), False),
	("Rejected", "Reconsider", "Applied", ("Registrar",), False),
)


def sync():
	for state, style in STATES.items():
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
				ignore_permissions=True
			)
	for action in ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True
			)

	if frappe.db.exists("Workflow", ADMISSION_WORKFLOW):
		workflow = frappe.get_doc("Workflow", ADMISSION_WORKFLOW)
	else:
		workflow = frappe.new_doc("Workflow")
		workflow.workflow_name = ADMISSION_WORKFLOW

	workflow.document_type = "Student Applicant"
	workflow.workflow_state_field = "application_status"
	workflow.is_active = 1
	workflow.send_email_alert = 0
	workflow.states = []
	for state, role in DOCUMENT_STATES:
		workflow.append("states", {"state": state, "doc_status": "0", "allow_edit": role})
	workflow.transitions = []
	for state, action, next_state, roles, self_approval in TRANSITIONS:
		for role in roles:
			workflow.append(
				"transitions",
				{
					"state": state,
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"allow_self_approval": 1 if self_approval else 0,
				},
			)
	workflow.save(ignore_permissions=True)
