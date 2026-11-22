"""Campus- and faculty-scoped test users for EduCore Demo University (development only).

    bench --site educore.localhost execute educore.access.test_users.create

The generic demo users (educore.access.demo_users: registrar@…, bursar@…) have no scope and stand for the
university-wide positions. This adds users limited the way real staff will be, through User Permissions:

- campus users: their Campus and its HR Branch (registry-officer.osh@…)
- faculty / department users: their Department node; a faculty includes its departments (dean.fst@…)
- both, where the job is both (faculty-officer.fst.whk@…, lecturer.comp.osh@…)
- students: their campus (student1.whk@…)
- edge cases: two positions, two campuses

Logins follow <position>[.<unit>][.<campus>]@educore.localhost, so the login says what the user should see.
Same password as the demo users. Re-running adds whatever is missing and changes nothing else.
"""

import os
import re

import frappe

from educore.access.demo_users import DEFAULT_PASSWORD, DOMAIN, _assert_development_site, new_user
from educore.setup.demo import CAMPUSES, UNITS

#: One user per position per campus
CAMPUS_POSITIONS = (
	"Campus Director",
	"Registry Officer",
	"Admissions Officer",
	"Examinations Officer",
	"Timetable Officer",
	"Student Fees Officer",
	"Cashier",
	"Financial Aid Officer",
	"Student Affairs Officer",
	"Accommodation Officer",
	"HR Officer",
	"Stores Officer",
	"Facilities Manager",
)
TEACHING_UNIT_TYPES = ("Academic Department", "School")
STUDENTS_PER_CAMPUS = 2


def _slug(text: str) -> str:
	return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _campus_names() -> dict[str, str]:
	return {code: frappe.db.get_value("Campus", {"campus_code": code}) for _, code, *_ in CAMPUSES}


def _unit(code: str) -> str:
	return frappe.db.get_value("Department", {"educore_unit_code": code})


def plan() -> list[dict]:
	"""Every scoped test user: login, name, positions and the records they are limited to"""
	campus = _campus_names()
	city = {code: name for name, code, *_ in CAMPUSES}
	users = []

	def add(login, first, last, positions, campuses=(), units=()):
		users.append(
			{
				"email": f"{login}@{DOMAIN}",
				"first_name": first,
				"last_name": last,
				"positions": list(positions),
				"campuses": [campus[c] for c in campuses],
				"units": [_unit(u) for u in units],
			}
		)

	for code in campus:
		place = city[code].replace(" Campus", "")
		for position in CAMPUS_POSITIONS:
			add(f"{_slug(position)}.{code.lower()}", position, place, [position], campuses=[code])
		for n in range(1, STUDENTS_PER_CAMPUS + 1):
			add(f"student{n}.{code.lower()}", "Student", f"{place} {n}", ["Student"], campuses=[code])

	for name, unit_type, code, campuses, children in UNITS:
		if unit_type != "Faculty":
			continue
		add(f"dean.{code.lower()}", "Dean", code, ["Dean"], units=[code])
		for c in campuses:
			add(f"faculty-officer.{code.lower()}.{c.lower()}", "Faculty Officer", f"{code} {city[c].replace(' Campus', '')}",
				["Faculty Officer"], campuses=[c], units=[code])
		for child_name, child_type, child_code, child_campuses in children:
			if child_type not in TEACHING_UNIT_TYPES:
				continue
			add(f"head-of-department.{child_code.lower()}", "Head of Department", child_code,
				["Head of Department"], units=[child_code])
			for c in child_campuses:
				add(f"lecturer.{child_code.lower()}.{c.lower()}", "Lecturer", f"{child_code} {city[c].replace(' Campus', '')}",
					["Lecturer"], campuses=[c], units=[child_code])

	# edge cases
	add("hod-lecturer.comp", "Head of Department and Lecturer", "COMP",
		["Head of Department", "Lecturer"], campuses=["WHK"], units=["COMP"])
	add("lecturer.accf.whk-osh", "Lecturer", "ACCF Windhoek and Oshakati", ["Lecturer"],
		campuses=["WHK", "OSH"], units=["ACCF"])
	add("registry-officer.whk-osh", "Registry Officer", "Windhoek and Oshakati", ["Registry Officer"],
		campuses=["WHK", "OSH"])
	return users


def _permit(user: str, doctype: str, value: str):
	if value and not frappe.db.exists("User Permission", {"user": user, "allow": doctype, "for_value": value}):
		frappe.get_doc(
			{"doctype": "User Permission", "user": user, "allow": doctype, "for_value": value, "apply_to_all_doctypes": 1}
		).insert(ignore_permissions=True)


def create(password: str | None = None) -> list[str]:
	_assert_development_site()
	if not frappe.db.exists("Campus", {"campus_code": CAMPUSES[0][1]}):
		frappe.throw("Create the demo university first: educore.setup.demo.create_demo_university")
	password = password or os.environ.get("EDUCORE_DEMO_PASSWORD") or DEFAULT_PASSWORD

	created = []
	# a bulk seed, like an import: Frappe otherwise stops at 60 new users an hour
	in_import, frappe.flags.in_import = frappe.flags.in_import, True
	try:
		_create_all(password, created)
	finally:
		frappe.flags.in_import = in_import

	frappe.db.commit()
	print(f"{len(created)} scoped test users created ({len(plan())} in the plan); password: {password}")
	return created


def _create_all(password: str, created: list[str]):
	for spec in plan():
		email = spec["email"]
		if not frappe.db.exists("User", email):
			new_user(
				email=email,
				first_name=spec["first_name"],
				last_name=spec["last_name"],
				password=password,
				positions=spec["positions"],
			)
			created.append(email)
		for campus in spec["campuses"]:
			_permit(email, "Campus", campus)
			_permit(email, "Branch", frappe.db.get_value("Campus", campus, "branch"))
		for unit in spec["units"]:
			_permit(email, "Department", unit)
