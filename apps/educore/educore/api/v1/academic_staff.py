"""Academic staff, for the faculty: the lecturers of each department, the classes they teach, and what is still
missing from their setup.

Every login with the Lecturer position has its lecturer (Instructor) record already (educore.academics.lecturers).
What can be missing is the teaching department, the campuses, or the HR staff record. The head of department or
the dean sets the department and campuses and marks a lecturer as left or active again; HR links the staff record.
Each person sees the lecturers of their own department or faculty (their User Permissions on Department), and of
their campus where they are limited to one, plus lecturers with no department yet.
"""

import frappe
from frappe import _

from educore.academics import lecturers, timetable
from educore.academics import workload as lecturer_workload

#: who sets a lecturer's department and campuses, and marks them left
EDIT_ROLES = ("Head of Department", "Dean", "System Manager")
#: who links the HR staff record
HR_ROLES = ("HR Manager", "HR User", "System Manager")
#: who reads the screen
READ_ROLES = (*EDIT_ROLES, *HR_ROLES, "Faculty Officer", "Registrar", "Campus Director", "Timetable Officer", "Quality Assurance Officer", "Executive Management")

#: who sets the workload rule (contact hours a week)
RULE_ROLES = ("Registrar", "System Manager")

READY, INCOMPLETE, LEFT = "Ready", "Incomplete", "Left"


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _require(roles):
	if not _has(roles):
		frappe.throw(_("Academic staff is the faculty's"), frappe.PermissionError)


def _short(department: str | None) -> str:
	return (department or "").rsplit(" - ", 1)[0]


def _departments() -> set[str]:
	"""The departments this person may see: their own department or faculty (with its departments), else all"""
	return set(frappe.get_list("Department", pluck="name", limit=0))


def _own_campuses() -> set[str]:
	return set(frappe.get_all("User Permission", filters={"user": frappe.session.user, "allow": "Campus"}, pluck="for_value"))


def _in_scope(doc: dict, departments: set[str], own_campuses: set[str]) -> bool:
	if doc["department"] and doc["department"] not in departments:
		return False
	return not (own_campuses and doc["campuses"] and not own_campuses & set(doc["campuses"]))


def _campuses_of(names: list[str]) -> dict[str, list[str]]:
	out: dict[str, list[str]] = {}
	for row in frappe.get_all(
		"Unit Campus", filters={"parenttype": "Instructor", "parent": ("in", names or [""])}, fields=["parent", "campus"], order_by="idx asc"
	):
		out.setdefault(row.parent, []).append(row.campus)
	return out


def _latest_year() -> str | None:
	years = frappe.get_all("Student Group", filters={"disabled": 0}, pluck="academic_year", distinct=True)
	return max(years, default=None)


def _missing(doc: dict) -> list[str]:
	missing = []
	if not doc["department"]:
		missing.append(_("Department"))
	if not doc["campuses"]:
		missing.append(_("Campus"))
	if not doc["employee"]:
		missing.append(_("HR staff record"))
	return missing


def _state(doc: dict) -> str:
	if doc["status"] == "Left":
		return LEFT
	return INCOMPLETE if _missing(doc) else READY


def _all() -> list[dict]:
	rows = frappe.get_all(
		"Instructor", fields=["name", "instructor_name", "department", "employee", "educore_user as user", "status"], order_by="instructor_name asc", limit=0
	)
	campuses = _campuses_of([r.name for r in rows])
	departments = _departments()
	own_campuses = _own_campuses()
	out = []
	for row in rows:
		doc = {**row, "user": row.user or lecturers.user_of(row.name), "campuses": campuses.get(row.name, [])}
		if _in_scope(doc, departments, own_campuses):
			out.append(doc)
	return out


def _get(name: str) -> dict:
	row = next((r for r in _all() if r["name"] == name), None)
	if not row:
		frappe.throw(_("{0} is not a lecturer in your department or faculty").format(name), frappe.PermissionError)
	return row


@frappe.whitelist(methods=["GET"])
def staff() -> dict:
	"""Every lecturer this person may see, with this year's classes and what is missing"""
	_require(READ_ROLES)
	rows = _all()
	year = _latest_year()
	classes: dict[str, int] = {}
	if year and rows:
		for r in frappe.db.sql(
			"""select i.instructor, count(distinct g.name) from `tabStudent Group Instructor` i
			join `tabStudent Group` g on g.name = i.parent
			where g.academic_year = %s and g.disabled = 0 and i.instructor in %s group by i.instructor""",
			(year, [r["name"] for r in rows]),
		):
			classes[r[0]] = r[1]
	return {
		"academic_year": year,
		"rows": [
			{
				"name": r["name"],
				"instructor_name": r["instructor_name"],
				"user": r["user"],
				"department": _short(r["department"]),
				"campuses": r["campuses"],
				"classes": classes.get(r["name"], 0),
				"missing": _missing(r),
				"state": _state(r),
			}
			for r in rows
		],
	}


@frappe.whitelist(methods=["GET"])
def lecturer(name: str) -> dict:
	"""One lecturer: department, campuses, HR staff record, positions and every class they teach"""
	_require(READ_ROLES)
	row = _get(name)
	groups = frappe.db.sql(
		"""select g.name, g.course, g.campus, g.academic_year, c.course_name, c.educore_course_code as code,
		(select count(*) from `tabStudent Group Student` s where s.parent = g.name and s.active = 1) as students
		from `tabStudent Group Instructor` i join `tabStudent Group` g on g.name = i.parent
		left join `tabCourse` c on c.name = g.course
		where i.instructor = %s and g.disabled = 0 order by g.academic_year desc, c.course_name asc""",
		name,
		as_dict=True,
	)
	employee = None
	if row["employee"]:
		employee = frappe.db.get_value(
			"Employee", row["employee"], ["name", "employee_name", "designation", "date_of_joining", "status"], as_dict=True
		)
	user = frappe.db.get_value("User", row["user"], ["name", "full_name", "enabled", "last_login"], as_dict=True) if row["user"] else None
	positions = (
		frappe.get_all("Has Role", filters={"parent": row["user"], "parenttype": "User"}, pluck="role") if row["user"] else []
	)
	can_edit = _has(EDIT_ROLES)
	can_link = _has(HR_ROLES) and not row["employee"]
	year, semester = _semester()
	departments = _departments()
	return {
		**{k: row[k] for k in ("name", "instructor_name", "user", "campuses", "employee")},
		"department": row["department"],
		"department_label": _short(row["department"]),
		"state": _state(row),
		"missing": _missing(row),
		"login": user,
		"staff_record": employee,
		"positions": sorted(p for p in positions if p in _ACADEMIC_POSITIONS),
		"classes": groups,
		"workload": {
			"academic_year": year,
			"semester": semester,
			"rule": lecturer_workload.rule(),
			**(lecturer_workload.for_lecturers(year, semester, [name])[name] if year else {}),
		}
		if row["status"] != "Left"
		else None,
		"can_edit": can_edit,
		"can_link": can_link,
		"choices": {
			"departments": sorted(
				({"name": d, "label": _short(d)} for d in departments if frappe.db.get_value("Department", d, "educore_unit_type") in lecturers.TEACHING_UNIT_TYPES),
				key=lambda d: d["label"],
			)
			if can_edit
			else [],
			"campuses": frappe.get_all("Campus", pluck="name", order_by="name asc") if can_edit else [],
		},
	}


#: the positions shown on a lecturer's page: the academic ones
_ACADEMIC_POSITIONS = ("Lecturer", "Head of Department", "Dean", "Faculty Officer", "Examinations Officer", "Timetable Officer", "Executive Management", "Campus Director")


@frappe.whitelist(methods=["POST"])
def save(name: str, department: str | None = None, campuses: list | str | None = None) -> dict:
	"""The lecturer's teaching department and the campuses they teach on"""
	_require(EDIT_ROLES)
	_get(name)
	doc = frappe.get_doc("Instructor", name)
	if department is not None:
		if department not in _departments() or frappe.db.get_value("Department", department, "educore_unit_type") not in lecturers.TEACHING_UNIT_TYPES:
			frappe.throw(_("Choose a teaching department in your faculty"))
		doc.department = department
	if campuses is not None:
		chosen = list(dict.fromkeys(frappe.parse_json(campuses) or []))
		if not chosen:
			frappe.throw(_("Choose at least one campus"))
		for campus in chosen:
			if not frappe.db.exists("Campus", campus):
				frappe.throw(_("{0} is not a campus").format(campus))
		doc.educore_campuses = []
		for campus in chosen:
			doc.append("educore_campuses", {"campus": campus})
	doc.flags.ignore_permissions = True
	doc.save()
	return lecturer(name)


@frappe.whitelist(methods=["POST"])
def set_left(name: str, left: int | str) -> dict:
	"""A lecturer who left (kept for the classes they taught; no longer allocated), or is back"""
	_require(EDIT_ROLES)
	_get(name)
	frappe.db.set_value("Instructor", name, "status", "Left" if frappe.utils.cint(left) else "Active")
	return lecturer(name)


@frappe.whitelist(methods=["GET"])
def unlinked_staff(search: str | None = None) -> list[dict]:
	"""HR staff records not yet linked to a lecturer, to link one"""
	_require(HR_ROLES)
	linked = set(frappe.get_all("Instructor", filters={"employee": ("is", "set")}, pluck="employee"))
	like = f"%{(search or '').strip()}%"
	rows = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		or_filters=[["employee_name", "like", like], ["name", "like", like]],
		fields=["name", "employee_name", "department", "user_id"],
		order_by="employee_name asc",
		limit=40,
	)
	return [{**r, "department": _short(r.department)} for r in rows if r.name not in linked][:20]


@frappe.whitelist(methods=["POST"])
def link_staff_record(name: str, employee: str) -> dict:
	"""HR: the lecturer's staff record; the staff record takes the lecturer's login when it has none"""
	_require(HR_ROLES)
	row = _get(name)
	if row["employee"]:
		frappe.throw(_("{0} already has a staff record").format(row["instructor_name"]))
	if frappe.db.exists("Instructor", {"employee": employee}):
		frappe.throw(_("{0} is linked to another lecturer").format(employee))
	user_id = frappe.db.get_value("Employee", employee, "user_id")
	if user_id and row["user"] and user_id != row["user"]:
		frappe.throw(_("{0} belongs to another login ({1})").format(employee, user_id))
	if not user_id and row["user"]:
		if frappe.db.exists("Employee", {"user_id": row["user"]}):
			frappe.throw(_("{0} already has another staff record").format(row["user"]))
		frappe.db.set_value("Employee", employee, "user_id", row["user"])
	frappe.db.set_value("Instructor", name, "employee", employee)
	if not row["department"]:
		department = frappe.db.get_value("Employee", employee, "department")
		if lecturers.is_academic_unit(department):
			frappe.db.set_value("Instructor", name, "department", department)
	return lecturer(name)


# --- workload ----------------------------------------------------------------------------------------------


def _semester(academic_year: str | None = None, semester: str | None = None) -> tuple[str | None, str]:
	"""The year and semester asked for, else the current one (else the latest year's first semester)"""
	from educore.api.v1.teaching_allocation import _years

	years = _years()
	current_year, current_semester = timetable.current_semester()
	academic_year = academic_year if academic_year in years else (current_year if current_year in years else (years[0] if years else None))
	return academic_year, semester if semester in timetable.SEMESTERS else current_semester


@frappe.whitelist(methods=["GET"])
def workload(academic_year: str | None = None, semester: str | None = None) -> dict:
	"""Each active lecturer's modules, students, contact hours a week and invigilation in a semester, against the rule"""
	_require(READ_ROLES)
	from educore.api.v1.teaching_allocation import _years

	academic_year, semester = _semester(academic_year, semester)
	rows = [r for r in _all() if r["status"] != "Left"]
	loads = lecturer_workload.for_lecturers(academic_year, semester, [r["name"] for r in rows]) if academic_year else {}
	return {
		"academic_year": academic_year,
		"academic_years": _years(),
		"semester": semester,
		"semesters": timetable.SEMESTERS,
		"rule": lecturer_workload.rule(),
		"can_edit_rule": _has(RULE_ROLES),
		"rows": [
			{
				"name": r["name"],
				"instructor_name": r["instructor_name"],
				"department": _short(r["department"]),
				**{k: v for k, v in loads.get(r["name"], {}).items() if k != "modules"},
				"modules": len(loads.get(r["name"], {}).get("modules", [])),
			}
			for r in rows
		],
	}


@frappe.whitelist(methods=["POST"])
def save_workload_rule(min_hours: float | str, max_hours: float | str) -> dict:
	"""The university's rule: contact hours a week, at least and at most"""
	if not _has(RULE_ROLES):
		frappe.throw(_("The workload rule is the Registrar's"), frappe.PermissionError)
	low, high = frappe.utils.flt(min_hours), frappe.utils.flt(max_hours)
	if low < 0 or high <= 0 or high > 60:
		frappe.throw(_("Contact hours a week are between 0 and 60"))
	if low > high:
		frappe.throw(_("The least is not above the most"))
	s = frappe.get_single(lecturer_workload.SETTINGS)
	s.min_hours, s.max_hours = low, high
	s.save(ignore_permissions=True)
	return lecturer_workload.rule()
