"""EduCore's roles and positions.

- A **role** is a permission building block. EduCore creates a role only where Frappe, ERPNext, HRMS or
  Education has none for the job (Registrar, Faculty Officer, Lecturer, …); their roles (Student,
  Instructor, HR Manager, Accounts User, …) are reused, never duplicated.
- A **position** is a Role Profile: the EduCore role of the job plus the upstream roles it needs. A person
  can hold several positions (a Head of Department who also lectures has both), and changing a position
  here changes everyone who holds it.

This file is the source of truth. sync() runs after install and every migrate: it creates missing roles,
keeps each EduCore role's desk access as defined, and sets each position's roles to exactly what is
listed. Change positions here (reviewed, versioned), not in the Role Profile form, or the next migrate
puts them back.

Campus and faculty scope (a campus registrar sees one campus; a dean, one faculty) is not a role: it will
be User Permissions on Campus and Faculty, once those records exist (AGENT.md 5.1.1).
"""

import frappe

#: EduCore's roles, with desk access (1: a staff user of the system; 0: an outside user on the portal)
ROLES = {
	# every employee
	"University Staff": 1,
	# may open Frappe's Desk: back-office positions only (AGENT.md 3.1, educore/access/desk.py)
	"Desk Access": 1,
	# executive and academic leadership
	"Executive Management": 1,
	"Campus Director": 1,
	"Dean": 1,
	"Head of Department": 1,
	# academic administration
	"Registrar": 1,
	"Registry Officer": 1,
	"Admissions Officer": 1,
	"Faculty Officer": 1,
	"Examinations Officer": 1,
	"Timetable Officer": 1,
	"Quality Assurance Officer": 1,
	# teaching
	"Lecturer": 1,
	# student services
	"Student Affairs Officer": 1,
	"Accommodation Officer": 1,
	# finance
	"Bursar": 1,
	"Finance Officer": 1,
	"Student Fees Officer": 1,
	"Cashier": 1,
	"Financial Aid Officer": 1,
	# campus operations
	"Facilities Manager": 1,
	# outside the staff: portal users
	"Applicant": 0,
	"Sponsor": 0,
	"External Examiner": 0,
}

#: Every staff position starts with these: EduCore's staff role and HRMS self-service (leave, payslips)
STAFF = ("University Staff", "Employee", "Employee Self Service")
#: Back-office positions also work in Frappe's Desk
DESK = (*STAFF, "Desk Access")

#: Positions (Role Profiles), grouped as the university is. Each lists every role the position gets.
POSITIONS = {
	"Executive and academic leadership": {
		"Vice-Chancellor": (*STAFF, "Executive Management", "Prepared Report User"),
		"Pro-Vice-Chancellor": (*STAFF, "Executive Management", "Prepared Report User"),
		"Campus Director": (*STAFF, "Campus Director", "Prepared Report User"),
		"Dean": (*STAFF, "Dean", "Prepared Report User"),
		"Head of Department": (*STAFF, "Head of Department"),
	},
	"Academic administration": {
		"Registrar": (*STAFF, "Registrar", "Education Manager", "Academics User", "Prepared Report User"),
		"Registry Officer": (*STAFF, "Registry Officer", "Academics User"),
		"Admissions Officer": (*STAFF, "Admissions Officer", "Academics User"),
		"Faculty Officer": (*STAFF, "Faculty Officer", "Academics User"),
		"Examinations Officer": (*STAFF, "Examinations Officer", "Academics User"),
		"Timetable Officer": (*STAFF, "Timetable Officer", "Academics User"),
		"Quality Assurance Officer": (*STAFF, "Quality Assurance Officer", "Prepared Report User"),
	},
	"Teaching": {
		"Lecturer": (*STAFF, "Lecturer", "Instructor"),
	},
	"Student services": {
		"Student Affairs Officer": (*STAFF, "Student Affairs Officer"),
		"Accommodation Officer": (*STAFF, "Accommodation Officer"),
	},
	"Finance": {
		"Bursar": (*DESK, "Bursar", "Accounts Manager", "Prepared Report User"),
		"Finance Officer": (*DESK, "Finance Officer", "Accounts User"),
		"Student Fees Officer": (*STAFF, "Student Fees Officer", "Accounts User"),
		"Cashier": (*STAFF, "Cashier", "Accounts User"),
		"Financial Aid Officer": (*STAFF, "Financial Aid Officer"),
		"Internal Auditor": (*DESK, "Auditor", "Prepared Report User"),
	},
	"Human resources": {
		"HR Manager": (*DESK, "HR Manager", "HR User"),
		"HR Officer": (*DESK, "HR User"),
		"Payroll Officer": (*DESK, "HR User"),
	},
	"Procurement and stores": {
		"Procurement Manager": (*DESK, "Purchase Manager", "Purchase Master Manager", "Purchase User"),
		"Procurement Officer": (*DESK, "Purchase User"),
		"Stores Officer": (*DESK, "Stock User"),
	},
	"Campus operations and ICT": {
		"Facilities Manager": (*STAFF, "Facilities Manager"),
		"ICT Administrator": (*DESK, "System Manager"),
	},
	"Students and outside users": {
		"Student": ("Student",),
		"Applicant": ("Applicant",),
		"Guardian": ("Guardian",),
		"Sponsor": ("Sponsor",),
		"External Examiner": ("External Examiner",),
	},
}


def all_positions() -> dict[str, tuple[str, ...]]:
	return {name: roles for group in POSITIONS.values() for name, roles in group.items()}


def sync():
	"""Creates EduCore's roles and positions, and keeps the positions as defined above"""
	for role, desk_access in ROLES.items():
		if frappe.db.exists("Role", role):
			if frappe.db.get_value("Role", role, "desk_access") != desk_access:
				frappe.db.set_value("Role", role, "desk_access", desk_access)
		else:
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk_access}).insert(
				ignore_permissions=True
			)

	for position, roles in all_positions().items():
		missing = [role for role in roles if not frappe.db.exists("Role", role)]
		if missing:
			# an upstream app is not installed on this site; the position waits for it
			frappe.log_error(
				title=f"EduCore position {position} not synced",
				message=f"Roles missing on this site: {', '.join(missing)}",
			)
			continue
		if frappe.db.exists("Role Profile", position):
			doc = frappe.get_doc("Role Profile", position)
			if {r.role for r in doc.roles} == set(roles):
				continue
			doc.roles = []
		else:
			doc = frappe.new_doc("Role Profile")
			doc.role_profile = position
		for role in roles:
			doc.append("roles", {"role": role})
		# saving a Role Profile updates the roles of every user who holds it
		doc.save(ignore_permissions=True)
