"""Examinations: marks, moderation, approval and published results (educore.academics.results).

- The lecturer enters a class's marks (only the classes they teach: User → Employee → Instructor on the class)
  and submits them.
- The head of department or the dean moderates (own department or faculty): adjusts a mark with a note, or
  returns the sheet to the lecturer; marks it moderated.
- The examinations officer (own campus) records the examination board's approval, or returns the sheet to the
  department, and publishes approved results; publishing sets academic standing.
- The Registrar sets the rules and, with the faculty officer, reads everything.
- A student sees their own published results only.
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from educore.academics import notify, results
from educore.api.v1.teaching import _instructors
from educore.api.v1.teaching_allocation import _courses

MODERATE_ROLES = ("Head of Department", "Dean", "System Manager")
EXAM_ROLES = ("Examinations Officer", "System Manager")
RULES_ROLES = ("Registrar", "System Manager")
#: Campus Director, Quality Assurance and Executive Management follow results; they decide nothing here
READ_ROLES = (*MODERATE_ROLES, *EXAM_ROLES, "Registrar", "Faculty Officer", "Campus Director", "Quality Assurance Officer", "Executive Management")
RULE_FIELDS = ("ca_weight", "exam_admission_ca", "pass_mark", "supplementary_from", "supplementary_cap", "probation_share", "grading_scale")


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _require(roles, message=None):
	if not _has(roles):
		frappe.throw(message or _("Not permitted"), frappe.PermissionError)


def _rules() -> dict:
	s = results.settings()
	return {**{f: s.get(f) for f in RULE_FIELDS}, "bands": [{"grade": g, "from": t} for g, t in results.grade_bands()]}


def _teaches(group: str) -> bool:
	mine = set(_instructors())
	return bool(mine) and bool(frappe.get_all("Student Group Instructor", filters={"parent": group, "instructor": ("in", list(mine))}, limit=1))


def _campus_scope() -> set[str]:
	from educore.access.scope import campuses

	return campuses()


def _in_scope(group: str) -> bool:
	"""A staff member's scope: the class's course in their department or faculty, and its campus theirs"""
	course, campus = frappe.db.get_value("Student Group", group, ["course", "campus"]) or (None, None)
	if course not in _courses():
		return False
	from educore.access.scope import campuses

	return not campus or campus in campuses()


def _sheet(group: str, create: bool = False):
	name = frappe.db.get_value("Mark Sheet", {"student_group": group})
	if name:
		return frappe.get_doc("Mark Sheet", name)
	if not create:
		return None
	g = frappe.get_doc("Student Group", group)
	doc = frappe.get_doc(
		{
			"doctype": "Mark Sheet",
			"student_group": group,
			"course": g.course,
			"campus": g.get("campus"),
			"academic_year": g.academic_year,
			"status": "Draft",
			"entries": [{"student": s.student, "student_name": s.student_name} for s in g.students if s.active],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _out(doc, group: str) -> dict:
	g = frappe.db.get_value("Student Group", group, ["course", "campus", "academic_year"], as_dict=True)
	code = frappe.db.get_value("Course", g.course, "educore_course_code")
	return {
		"group": group,
		"course": g.course,
		"code": code,
		"campus": g.campus,
		"academic_year": g.academic_year,
		"lecturers": frappe.get_all("Student Group Instructor", filters={"parent": group}, pluck="instructor_name"),
		"status": doc.status if doc else "Not started",
		"return_note": doc.return_note if doc else None,
		"entries": [
			{
				**{f: e.get(f) for f in ("student", "student_name", "absent", "grade", "result", "moderation_note", "first_result")},
				# marks as numbers, empty when not entered; the final mark only once there is a result
				"ca_mark": results.mark(e.ca_mark),
				"exam_mark": results.mark(e.exam_mark),
				"supp_exam_mark": results.mark(e.supp_exam_mark),
				"final_mark": e.final_mark if e.result and e.final_mark is not None and e.result not in (results.NOT_ADMITTED, results.ABSENT) else None,
				"first_final_mark": e.first_final_mark if e.first_result else None,
				"writes_supplementary": bool(results.second_sitting(e)),
				# "Supplementary" or "Special": the examination this student writes at the supplementary sitting
				"sitting": results.second_sitting(e),
				"special_reason": e.special_reason,
			}
			for e in (doc.entries if doc else [])
		],
		# the supplementary sitting, once the results are published and someone has a supplementary result
		"supp_status": (doc.supp_status or ("Open" if any(results.second_sitting(e) for e in doc.entries) and doc.status == "Published" else None)) if doc else None,
		"supp_board_reference": doc.supp_board_reference if doc else None,
		"summary": results.summary(doc) if doc else None,
		"trail": {f: (str(doc.get(f)) if doc and doc.get(f) else None) for f in (
			"submitted_by", "submitted_on", "moderated_by", "moderated_on", "approved_by", "approved_on", "board_reference", "published_on")},
		"rules": _rules(),
	}


# --- the lecturer -------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def my_sheet(group: str) -> dict:
	"""The marks of a class the lecturer teaches (the sheet is started with its class list the first time)"""
	if not _teaches(group):
		frappe.throw(_("You do not teach this class"), frappe.PermissionError)
	return {**_out(_sheet(group, create=True), group), "can_edit": True}


@frappe.whitelist(methods=["POST"])
def save_marks(group: str, entries: list | str) -> dict:
	if not _teaches(group):
		frappe.throw(_("You do not teach this class"), frappe.PermissionError)
	doc = _sheet(group, create=True)
	if doc.status != "Draft":
		frappe.throw(_("The marks are submitted; the department returns them if they need changing"))
	_apply(doc, entries)
	doc.save(ignore_permissions=True)
	return {**_out(doc, group), "can_edit": True}


def _apply(doc, entries, note: str | None = None):
	given = {e.get("student"): e for e in (frappe.parse_json(entries) or [])}
	for entry in doc.entries:
		if entry.student not in given:
			continue
		e = given[entry.student]
		before = (entry.ca_mark, entry.exam_mark, entry.absent)
		entry.ca_mark = results.store(e.get("ca_mark"))
		entry.exam_mark = results.store(e.get("exam_mark"))
		entry.absent = 1 if e.get("absent") else 0
		if note and before != (entry.ca_mark, entry.exam_mark, entry.absent):
			entry.moderation_note = note
	results.work_out_sheet(doc)


@frappe.whitelist(methods=["POST"])
def submit(group: str) -> dict:
	if not _teaches(group):
		frappe.throw(_("You do not teach this class"), frappe.PermissionError)
	doc = _sheet(group)
	if not doc or doc.status != "Draft":
		frappe.throw(_("Nothing to submit"))
	results.work_out_sheet(doc)
	missing = [e.student_name or e.student for e in doc.entries if not e.result]
	if missing:
		frappe.throw(_("Marks still missing for: {0}").format(", ".join(missing)))
	doc.update({"status": "Submitted", "submitted_by": frappe.session.user, "submitted_on": now_datetime(), "return_note": None})
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Marks submitted"))
	return {**_out(doc, group), "can_edit": False}


# --- the supplementary sitting (lecturer, then the examinations officer) -----------------------------


def _supp_sheet(group: str):
	if not _teaches(group):
		frappe.throw(_("You do not teach this class"), frappe.PermissionError)
	doc = _sheet(group)
	if not doc or doc.status != "Published" or doc.supp_status not in (None, "", "Open"):
		frappe.throw(_("The supplementary marks are not open for this class"))
	if not any(results.second_sitting(e) for e in doc.entries):
		frappe.throw(_("No student in this class writes a supplementary or special examination"))
	return doc


@frappe.whitelist(methods=["POST"])
def save_supplementary(group: str, entries: list | str) -> dict:
	"""The supplementary examination marks of the students who write it"""
	doc = _supp_sheet(group)
	given = {e.get("student"): e.get("supp_exam_mark") for e in (frappe.parse_json(entries) or [])}
	for entry in doc.entries:
		if entry.student in given and results.second_sitting(entry):
			value = results.mark(given[entry.student])
			if value is not None and not 0 <= value <= 100:
				frappe.throw(_("{0}: the supplementary mark must be between 0 and 100").format(entry.student_name))
			entry.supp_exam_mark = results.store(value)
	doc.supp_status = "Open"
	doc.save(ignore_permissions=True)
	return {**_out(doc, group), "can_edit": False}


@frappe.whitelist(methods=["POST"])
def submit_supplementary(group: str) -> dict:
	doc = _supp_sheet(group)
	missing = [e.student_name for e in doc.entries if results.second_sitting(e) and results.mark(e.supp_exam_mark) is None]
	if missing:
		frappe.throw(_("Supplementary marks still missing for: {0}").format(", ".join(missing)))
	doc.update({"supp_status": "Submitted", "supp_submitted_on": now_datetime()})
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Supplementary marks submitted"))
	return {**_out(doc, group), "can_edit": False}


@frappe.whitelist(methods=["POST"])
def publish_supplementary(group: str, board_reference: str) -> dict:
	"""The supplementary results, approved by the examination board, to the students; standing follows"""
	_require(EXAM_ROLES)
	if not _in_scope(group):
		frappe.throw(_("This class is not in your department, faculty or campus"), frappe.PermissionError)
	doc = _sheet(group)
	if not doc or doc.supp_status != "Submitted":
		frappe.throw(_("No supplementary marks are waiting to be published"))
	if not (board_reference or "").strip():
		frappe.throw(_("Give the examination board meeting that approved the results"))
	rules_, bands = results.settings(), results.grade_bands()
	for entry in doc.entries:
		sitting = results.second_sitting(entry)
		if sitting == "Special":
			results.work_out_special(entry, rules_, bands)
		elif sitting == "Supplementary":
			results.work_out_supplementary(entry, rules_, bands)
	doc.update({"supp_status": "Published", "supp_board_reference": board_reference.strip(), "supp_published_on": now_datetime()})
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Supplementary results published: {0}").format(board_reference.strip()))
	results.update_standing([e.student for e in doc.entries], doc.academic_year)
	for entry in doc.entries:
		if results.second_sitting(entry):
			notify.send(entry.student, "supplementary_published", doc, courses=doc.course)
	return sheet(group)


@frappe.whitelist(methods=["POST"])
def grant_special(group: str, student: str, reason: str) -> dict:
	"""A special examination for a student absent from the examination with a valid reason (illness,
	bereavement), granted by the examinations office; written at the supplementary sitting"""
	_require(EXAM_ROLES)
	if not _in_scope(group):
		frappe.throw(_("This class is not in your department, faculty or campus"), frappe.PermissionError)
	if not (reason or "").strip():
		frappe.throw(_("Give the reason for the special examination"))
	doc = _sheet(group)
	if not doc or doc.status != "Published" or doc.supp_status in ("Submitted", "Published"):
		frappe.throw(_("Special examinations are granted on published results, before the supplementary sitting closes"))
	entry = next((e for e in doc.entries if e.student == student), None)
	if not entry or entry.result != results.ABSENT:
		frappe.throw(_("A special examination is for a student absent from the examination"))
	entry.special_granted, entry.special_reason = 1, reason.strip()
	doc.supp_status = "Open"
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Special examination granted to {0}: {1}").format(entry.student_name, reason.strip()))
	return sheet(group)


# --- staff: the list and a sheet ----------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def sheets(academic_year: str | None = None) -> dict:
	"""Every class of the year this person may see, with where its marks stand"""
	_require(READ_ROLES)
	years = sorted(set(frappe.get_all("Student Group", filters={"group_based_on": "Course"}, pluck="academic_year")), reverse=True)
	academic_year = academic_year or (years[0] if years else None)
	courses = _courses()
	groups = frappe.get_all(
		"Student Group",
		filters={
			"group_based_on": "Course",
			"academic_year": academic_year,
			"disabled": 0,
			"course": ("in", list(courses) or [""]),
			"campus": ("in", list(_campus_scope()) or [""]),
		},
		fields=["name", "course", "campus"],
		order_by="name asc",
		limit=0,
	)
	by_group = {
		s.student_group: s
		for s in frappe.get_all("Mark Sheet", filters={"student_group": ("in", [g.name for g in groups] or [""])}, fields=["name", "student_group", "status"])
	}
	rows = []
	for g in groups:
		sheet = by_group.get(g.name)
		summary = results.summary(frappe.get_doc("Mark Sheet", sheet.name)) if sheet else None
		rows.append({
			"group": g.name,
			"course": g.course,
			"code": courses[g.course].code,
			"campus": g.campus,
			"lecturers": frappe.get_all("Student Group Instructor", filters={"parent": g.name}, pluck="instructor_name"),
			"students": frappe.db.count("Student Group Student", {"parent": g.name, "active": 1}),
			"status": sheet.status if sheet else "Not started",
			"pass_rate": summary["pass_rate"] if summary else None,
			"supp_status": frappe.db.get_value("Mark Sheet", sheet.name, "supp_status") if sheet else None,
		})
	return {
		"academic_year": academic_year,
		"academic_years": years,
		"rows": rows,
		"can_publish": _has(EXAM_ROLES),
		"can_set_rules": _has(RULES_ROLES),
	}


@frappe.whitelist(methods=["GET"])
def sheet(group: str) -> dict:
	_require(READ_ROLES)
	if not _in_scope(group):
		frappe.throw(_("This class is not in your department, faculty or campus"), frappe.PermissionError)
	doc = _sheet(group)
	status = doc.status if doc else None
	return {
		**_out(doc, group),
		"can_moderate": _has(MODERATE_ROLES) and status == "Submitted",
		"can_approve": _has(EXAM_ROLES) and status == "Moderated",
		"can_publish": _has(EXAM_ROLES) and status == "Approved",
		"can_publish_supp": _has(EXAM_ROLES) and status == "Published" and bool(doc and doc.supp_status == "Submitted"),
		"can_grant_special": _has(EXAM_ROLES) and status == "Published" and bool(doc) and doc.supp_status not in ("Submitted", "Published"),
	}


# --- moderation, approval, publication ----------------------------------------------------------------


def _staff_sheet(group: str, roles, status: str):
	_require(roles)
	if not _in_scope(group):
		frappe.throw(_("This class is not in your department, faculty or campus"), frappe.PermissionError)
	doc = _sheet(group)
	if not doc or doc.status != status:
		frappe.throw(_("The marks are not waiting for this step"))
	return doc


@frappe.whitelist(methods=["POST"])
def moderate(group: str, entries: list | str | None = None, note: str | None = None) -> dict:
	"""The department's moderation: marks adjusted (with the reason), then moderated"""
	doc = _staff_sheet(group, MODERATE_ROLES, "Submitted")
	if entries:
		if not (note or "").strip():
			frappe.throw(_("Give the reason for changing marks"))
		_apply(doc, entries, note.strip())
	doc.update({"status": "Moderated", "moderated_by": frappe.session.user, "moderated_on": now_datetime()})
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Marks moderated") + (f": {note.strip()}" if note else ""))
	return sheet(group)


@frappe.whitelist(methods=["POST"])
def return_sheet(group: str, note: str) -> dict:
	"""Back one step with a note: the department to the lecturer, the examinations office to the department"""
	if not (note or "").strip():
		frappe.throw(_("Say what needs changing"))
	doc = _sheet(group)
	if doc and doc.status == "Submitted" and _has(MODERATE_ROLES):
		doc = _staff_sheet(group, MODERATE_ROLES, "Submitted")
		doc.status = "Draft"
	elif doc and doc.status == "Moderated" and _has(EXAM_ROLES):
		doc = _staff_sheet(group, EXAM_ROLES, "Moderated")
		doc.status = "Submitted"
	else:
		frappe.throw(_("The marks cannot be returned from here"), frappe.PermissionError)
	doc.return_note = note.strip()
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Marks returned: {0}").format(note.strip()))
	return sheet(group)


@frappe.whitelist(methods=["POST"])
def approve(group: str, board_reference: str) -> dict:
	"""The examination board's approval, recorded by the examinations officer"""
	doc = _staff_sheet(group, EXAM_ROLES, "Moderated")
	if not (board_reference or "").strip():
		frappe.throw(_("Give the examination board meeting that approved the results"))
	doc.update({"status": "Approved", "approved_by": frappe.session.user, "approved_on": now_datetime(), "board_reference": board_reference.strip()})
	doc.save(ignore_permissions=True)
	doc.add_comment("Workflow", _("Results approved: {0}").format(board_reference.strip()))
	return sheet(group)


@frappe.whitelist(methods=["POST"])
def publish(groups: list | str) -> dict:
	"""Approved results to the students; academic standing follows"""
	_require(EXAM_ROLES)
	published, students, years = 0, [], set()
	#: student: (their courses published now, a sheet to reference)
	told: dict[str, tuple[list[str], object]] = {}
	for group in frappe.parse_json(groups) or []:
		doc = _staff_sheet(group, EXAM_ROLES, "Approved")
		doc.update({"status": "Published", "published_on": now_datetime()})
		doc.save(ignore_permissions=True)
		doc.add_comment("Workflow", _("Results published"))
		students += [e.student for e in doc.entries]
		years.add(doc.academic_year)
		for e in doc.entries:
			told.setdefault(e.student, ([], doc))[0].append(doc.course)
		published += 1
	for year in years:
		results.update_standing([s for s in students], year)
	# one email per student, however many classes were published together
	for student, (courses, doc) in told.items():
		notify.send(student, "results_published", doc, courses=notify.courses(courses))
	return {"published": published}


# --- the rules ----------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def rules() -> dict:
	_require(READ_ROLES)
	return {**_rules(), "grading_scales": frappe.get_all("Grading Scale", filters={"docstatus": 1}, pluck="name"), "can_edit": _has(RULES_ROLES)}


@frappe.whitelist(methods=["POST"])
def save_rules(data: dict | str) -> dict:
	_require(RULES_ROLES, _("The examination rules are the Registrar's"))
	data = frappe.parse_json(data)
	s = frappe.get_single("Examination Settings")
	for field in RULE_FIELDS:
		if field in data:
			s.set(field, data[field])
	for field in ("ca_weight", "exam_admission_ca", "pass_mark", "supplementary_from", "probation_share"):
		if not 0 <= flt(s.get(field)) <= 100:
			frappe.throw(_("{0} must be between 0 and 100").format(s.meta.get_label(field)))
	if flt(s.supplementary_from) > flt(s.pass_mark):
		frappe.throw(_("The supplementary band starts below the pass mark"))
	if s.grading_scale and not frappe.db.exists("Grading Scale", {"name": s.grading_scale, "docstatus": 1}):
		frappe.throw(_("Choose a grading scale"))
	s.save(ignore_permissions=True)
	return rules()


# --- the student --------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def my_results() -> dict:
	"""The signed-in student's published results, by year"""
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	if not student:
		frappe.throw(_("This page is for students."), frappe.PermissionError)
	rows = frappe.db.sql(
		"""select ms.academic_year, ms.course, ms.student_group, e.final_mark, e.grade, e.result, ms.published_on
		from `tabMark Sheet Entry` e join `tabMark Sheet` ms on ms.name = e.parent
		where ms.status = 'Published' and e.student = %s order by ms.academic_year desc, ms.course""",
		student,
		as_dict=True,
	)
	from educore.registration.rules import credits

	for r in rows:
		r["code"] = frappe.db.get_value("Course", r.course, "educore_course_code")
		r["credits"] = credits(r.course)
		r["published_on"] = str(r.published_on) if r.published_on else None
		if r.result in (results.NOT_ADMITTED, results.ABSENT):
			r["final_mark"] = None
	return {"results": rows}
