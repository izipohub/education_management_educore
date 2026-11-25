"""Re-registration of continuing students for a new academic year.

A returning student registers online in the Vue app: they choose the year's courses from their programme's
curriculum and submit; the faculty officer approves (or returns it with a note), and approving submits the year's
Program Enrollment, which invoices the year's fees (educore.finance.student_fees), with the late fee when they
registered after the period closed.

What the university decides lives in Registration Settings (outstanding balance allowed, deposit, credit limit,
approval) and Registration Period (when each year's registration opens, closes and late registration ends). What
blocks a student is listed by blockers(), in plain words; academic standing is set on the Student by the faculty
until the examinations module sets it.
"""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, getdate, nowdate

DRAFT, SUBMITTED, RETURNED, APPROVED = "Draft", "Submitted", "Returned", "Approved"
BLOCKING_STANDING = ("On hold", "Excluded")


#: Registration Settings: the default, written once if the site has never had a value
SETTINGS_DEFAULTS = {
	"max_outstanding": 0,
	"deposit_type": "Percent of the year's fees",
	"deposit_value": 20,
	"max_credits": 0,
	"approval_needed": 1,
}


def ensure_defaults():
	"""From every migrate: the defaults above for anything a site has never set"""
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = 'Registration Settings'"))
	for field, value in SETTINGS_DEFAULTS.items():
		if field not in stored:
			frappe.db.set_single_value("Registration Settings", field, value)


def settings():
	return frappe.get_cached_doc("Registration Settings")


# --- the period ----------------------------------------------------------------------------------------


def period_state(period) -> str:
	"""upcoming, open, late or closed, today"""
	today = getdate(nowdate())
	if today < getdate(period.opens_on):
		return "upcoming"
	if today <= getdate(period.closes_on):
		return "open"
	if period.late_until and today <= getdate(period.late_until):
		return "late"
	return "closed"


def current_period():
	"""The registration period to show: the one open now, else the next one, else the latest"""
	periods = [frappe.get_cached_doc("Registration Period", name) for name in frappe.get_all("Registration Period", pluck="name")]
	if not periods:
		return None
	by_start = sorted(periods, key=lambda p: getdate(p.opens_on))
	for period in by_start:
		if period_state(period) in ("open", "late"):
			return period
	upcoming = [p for p in by_start if period_state(p) == "upcoming"]
	return upcoming[0] if upcoming else by_start[-1]


# --- the student ---------------------------------------------------------------------------------------


def enrolments(student: str) -> list:
	return frappe.get_all(
		"Program Enrollment",
		filters={"student": student, "docstatus": 1},
		fields=["name", "academic_year", "program", "educore_programme_offering", "enrollment_date"],
		order_by="enrollment_date desc",
	)


def year_of_study(student: str, academic_year: str) -> int:
	earlier = {e.academic_year for e in enrolments(student) if e.academic_year != academic_year}
	return len(earlier) + 1


def credits(course: str) -> int:
	return frappe.get_cached_value("Course", course, "educore_credits") or 0


def curriculum(program: str) -> list[dict]:
	"""The programme's courses with their year of study and semester"""
	doc = frappe.get_cached_doc("Program", program)
	return [
		{
			"course": row.course,
			"course_name": row.course_name or row.course,
			"code": frappe.get_cached_value("Course", row.course, "educore_course_code"),
			"credits": credits(row.course),
			"year": row.get("educore_year") or 1,
			"semester": row.get("educore_semester") or "Year",
			"required": bool(row.required),
			"prerequisites": prerequisites(row.course),
		}
		for row in doc.courses
	]


def prerequisites(course: str) -> list[str]:
	"""The courses to pass before this one (set on the course, wherever it is taught)"""
	return frappe.get_all("Course Prerequisite", filters={"parent": course, "parenttype": "Course"}, pluck="prerequisite", order_by="idx")


# --- what a student has passed, and what is open to them ----------------------------------------------

PASSED, REPEAT, BLOCKED, OPEN = "passed", "repeat", "blocked", "open"


def results_by_course(student: str) -> dict[str, str]:
	"""The student's latest published result per course (educore.academics.results)"""
	rows = frappe.db.sql(
		"""select ms.course, e.result from `tabMark Sheet Entry` e join `tabMark Sheet` ms on ms.name = e.parent
		where ms.status = 'Published' and e.student = %s order by ms.academic_year asc, ms.published_on asc""",
		student,
		as_dict=True,
	)
	latest: dict[str, str] = {}
	for row in rows:
		# a pass stands; a later attempt replaces an earlier failure
		if latest.get(row.course) != "Pass":
			latest[row.course] = row.result
	return latest


def course_states(student: str, program: str, year: int) -> dict[str, dict]:
	"""Each curriculum course for this student: passed already, a repeat (not passed earlier), blocked by a
	prerequisite not yet passed (with which), or open"""
	results = results_by_course(student)
	passed = {c for c, r in results.items() if r == "Pass"}
	states = {}
	for c in curriculum(program):
		if c["course"] in passed:
			states[c["course"]] = {"state": PASSED, "missing": []}
			continue
		missing = [p for p in c["prerequisites"] if p not in passed]
		if missing:
			states[c["course"]] = {"state": BLOCKED, "missing": missing}
		elif c["course"] in results and c["year"] < year + 1:
			states[c["course"]] = {"state": REPEAT, "missing": []}
		else:
			states[c["course"]] = {"state": OPEN, "missing": []}
	return states


#: the order courses are shown in, and how each period reads
SEMESTER_ORDER = {"Semester 1": 1, "Semester 2": 2, "Year": 3}
SEMESTER_LABELS = {"Semester 1": "Semester 1", "Semester 2": "Semester 2", "Year": "Full year"}


def semesters(program: str) -> dict[str, str]:
	"""When each of the programme's courses runs, from its curriculum: course: Semester 1, Semester 2 or Year"""
	return {c["course"]: c["semester"] for c in curriculum(program)} if program else {}


def customer(student: str) -> str | None:
	return frappe.db.get_value("Student", student, "customer")


def outstanding(student: str, academic_year: str | None = None) -> float:
	"""Fees still owed on invoices from earlier years (this year's registration invoice not counted)"""
	party = customer(student)
	if not party:
		return 0.0
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"customer": party, "docstatus": 1, "outstanding_amount": (">", 0)},
		fields=["outstanding_amount", "educore_program_enrollment"],
	)
	total = 0.0
	for row in rows:
		if academic_year and row.educore_program_enrollment:
			if frappe.db.get_value("Program Enrollment", row.educore_program_enrollment, "academic_year") == academic_year:
				continue
		total += flt(row.outstanding_amount)
	return total


def paid_in_advance(student: str) -> float:
	"""Payments received and not yet set against an invoice: the deposit towards the new year"""
	party = customer(student)
	if not party:
		return 0.0
	return flt(
		frappe.db.sql(
			"""select sum(unallocated_amount) from `tabPayment Entry`
			where docstatus = 1 and payment_type = 'Receive' and party_type = 'Customer' and party = %s""",
			party,
		)[0][0]
	)


def year_fees(offering: str, academic_year: str) -> float:
	from educore.finance.student_fees import fee_structure_for

	structure = fee_structure_for(offering, academic_year)
	return flt(frappe.db.get_value("Fee Structure", structure, "total_amount")) if structure else 0.0


def deposit_required(offering: str, academic_year: str) -> float:
	rules = settings()
	if rules.deposit_type == "Amount":
		return flt(rules.deposit_value, 2)
	if rules.deposit_type == "Percent of the year's fees":
		return flt(year_fees(offering, academic_year) * flt(rules.deposit_value) / 100, 2)
	return 0.0


def _nad(amount: float) -> str:
	return f"N$ {fmt_money(amount, precision=2)}"


def blockers(student: str, offering: str, period) -> list[str]:
	"""What stops this student registering for the period's year, in plain words (empty: nothing)"""
	found = []
	state = period_state(period)
	if state == "upcoming":
		found.append(_("Registration for {0} opens on {1}").format(period.academic_year, frappe.utils.formatdate(period.opens_on)))
	elif state == "closed":
		found.append(_("Registration for {0} has closed").format(period.academic_year))

	enabled, interrupted_until = frappe.db.get_value("Student", student, ["enabled", "educore_interrupted_until"])
	if not enabled:
		found.append(_("Your studies are cancelled; apply again to return"))
	elif interrupted_until and str(period.academic_year) < str(interrupted_until):
		found.append(_("Your studies are interrupted; you register again for {0}").format(interrupted_until))

	standing, note = frappe.db.get_value("Student", student, ["educore_academic_standing", "educore_standing_note"])
	if standing in BLOCKING_STANDING:
		found.append(_("Academic standing: {0}{1}").format(standing, f". {note}" if note else ""))

	owed = outstanding(student, period.academic_year)
	allowed = flt(settings().max_outstanding)
	if owed > allowed:
		found.append(_("Outstanding fees: {0}").format(_nad(owed)))

	needed = deposit_required(offering, period.academic_year)
	paid = paid_in_advance(student)
	if needed and paid < needed:
		found.append(
			_("Registration deposit: {0} due").format(_nad(needed))
			if not paid
			else _("Registration deposit: {0} of {1} paid").format(_nad(paid), _nad(needed))
		)
	return found


def check_courses(program: str, year: int, chosen: list[str], student: str | None = None):
	"""Every course is on the programme and open to the student (not passed already, prerequisites passed); the
	year's required courses and the required repeats are all chosen; within the credit limit"""
	courses = {c["course"]: c for c in curriculum(program)}
	unknown = [c for c in chosen if c not in courses]
	if unknown:
		frappe.throw(_("{0} is not part of the programme").format(", ".join(unknown)))
	states = course_states(student, program, year) if student else {}
	for course in chosen:
		state = states.get(course, {})
		if state.get("state") == PASSED:
			frappe.throw(_("{0} is passed already").format(courses[course]["course_name"]))
		if state.get("state") == BLOCKED:
			frappe.throw(
				_("{0} needs {1} passed first").format(courses[course]["course_name"], ", ".join(state["missing"]))
			)
	open_required = [
		c for c in courses.values()
		if c["required"] and states.get(c["course"], {}).get("state") not in (PASSED, BLOCKED)
		and (c["year"] == year or states.get(c["course"], {}).get("state") == REPEAT)
	]
	missing = [c["course_name"] for c in open_required if c["course"] not in chosen]
	if missing:
		frappe.throw(_("Required this year: {0}").format(", ".join(missing)))
	limit = settings().max_credits or 0
	total = sum(courses[c]["credits"] for c in chosen)
	if limit and total > limit:
		frappe.throw(_("{0} credits chosen; at most {1} a year").format(total, limit))
	if not chosen:
		frappe.throw(_("Choose the year's courses"))
