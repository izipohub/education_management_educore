"""Keeping Moodle in step with EduCore's classes (AGENT.md 6.3 to 6.5).

EduCore is the system of record for who studies and teaches what; Moodle holds the learning. For each class (a
course Student Group, educore.api.v1.teaching_allocation) the sync makes sure that, in Moodle:

- the class's course exists (found by its idnumber, the class's name; made in the campus's category);
- each active student and each lecturer has a Moodle user (found by idnumber: the student number, or the
  lecturer's Employee ID; made with their email as username);
- students are enrolled as students and lecturers as teachers (manual enrolment); students no longer on the class
  list are unenrolled.

Every step looks before it makes, so running it again changes nothing (idempotent); a class that fails keeps its
error and is tried again on the next run. It runs hourly, and on demand from the Integrations screen; it does
nothing until ICT connects Moodle (Learning Platform Settings).
"""

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

TIMEOUT = 30


class MoodleError(Exception):
	pass


def settings():
	return frappe.get_single("Learning Platform Settings")


def _flatten(params: dict, prefix: str = "") -> dict:
	"""Moodle's REST format: users[0][username]=..."""
	out = {}
	for key, value in params.items():
		name = f"{prefix}[{key}]" if prefix else str(key)
		if isinstance(value, dict):
			out.update(_flatten(value, name))
		elif isinstance(value, (list, tuple)):
			out.update(_flatten(dict(enumerate(value)), name))
		elif value is not None:
			out[name] = value
	return out


class MoodleClient:
	"""Moodle's web services (REST, JSON), with the site's token"""

	def __init__(self, url: str, token: str):
		self.endpoint = url.rstrip("/") + "/webservice/rest/server.php"
		self.token = token

	@classmethod
	def from_settings(cls) -> "MoodleClient":
		s = settings()
		if not s.moodle_url or not s.get_password("moodle_token", raise_exception=False):
			raise MoodleError(_("Moodle is not connected: give its address and web service token"))
		return cls(s.moodle_url, s.get_password("moodle_token"))

	def call(self, function: str, **params):
		data = {"wstoken": self.token, "wsfunction": function, "moodlewsrestformat": "json", **_flatten(params)}
		response = requests.post(self.endpoint, data=data, timeout=TIMEOUT)
		response.raise_for_status()
		result = response.json() if response.content else None
		if isinstance(result, dict) and result.get("exception"):
			raise MoodleError(f"{function}: {result.get('message') or result.get('errorcode')}")
		return result


# --- users --------------------------------------------------------------------------------------------


def _ensure_user(client: MoodleClient, idnumber: str, first: str, last: str, email: str) -> int:
	found = client.call("core_user_get_users_by_field", field="idnumber", values=[idnumber])
	if found:
		return found[0]["id"]
	username = (email or idnumber).strip().lower()
	found = client.call("core_user_get_users_by_field", field="username", values=[username])
	if found:
		return found[0]["id"]
	sso = settings().sign_in == "Single sign-on"
	user = {
		"username": username,
		"firstname": first or idnumber,
		"lastname": last or "-",
		"email": email,
		"idnumber": idnumber,
		"auth": "oauth2" if sso else "manual",
	}
	if not sso:
		user["createpassword"] = 1
	return client.call("core_user_create_users", users=[user])[0]["id"]


def _student_user(client: MoodleClient, student: str) -> int | None:
	s = frappe.db.get_value("Student", student, ["first_name", "last_name", "student_email_id", "user"], as_dict=True)
	if not s:
		return None
	return _ensure_user(client, student, s.first_name, s.last_name, s.user or s.student_email_id)


def _lecturer_user(client: MoodleClient, instructor: str) -> int | None:
	employee = frappe.db.get_value("Instructor", instructor, "employee")
	if employee:
		e = frappe.db.get_value("Employee", employee, ["first_name", "last_name", "user_id", "company_email", "personal_email"], as_dict=True)
		email = e.user_id or e.company_email or e.personal_email
		if email:
			return _ensure_user(client, employee, e.first_name, e.last_name, email)
	# no HR staff record yet: the lecturer's own login
	user = frappe.db.get_value("Instructor", instructor, "educore_user")
	if not user:
		return None
	u = frappe.db.get_value("User", user, ["first_name", "last_name", "email"], as_dict=True)
	return _ensure_user(client, instructor, u.first_name, u.last_name or "", u.email or user)


# --- courses ------------------------------------------------------------------------------------------


def _category(client: MoodleClient, campus: str | None) -> int:
	"""The campus's course category (made once), or Moodle's default category"""
	if not campus or not settings().campus_categories:
		return 1
	idnumber = f"campus-{frappe.db.get_value('Campus', campus, 'campus_code') or campus}"
	found = client.call("core_course_get_categories", criteria=[{"key": "idnumber", "value": idnumber}])
	if found:
		return found[0]["id"]
	return client.call("core_course_create_categories", categories=[{"name": campus, "idnumber": idnumber, "parent": 0}])[0]["id"]


def _ensure_course(client: MoodleClient, group) -> int:
	found = client.call("core_course_get_courses_by_field", field="idnumber", value=group.name)
	courses = (found or {}).get("courses") or []
	if courses:
		return courses[0]["id"]
	course_name = frappe.db.get_value("Course", group.course, "course_name") or group.course
	return client.call(
		"core_course_create_courses",
		courses=[
			{
				"fullname": f"{course_name} ({group.get('campus') or ''} {group.academic_year})".replace("( ", "("),
				"shortname": group.name,
				"idnumber": group.name,
				"categoryid": _category(client, group.get("campus")),
			}
		],
	)[0]["id"]


# --- a class ------------------------------------------------------------------------------------------


def sync_class(group_name: str, client: MoodleClient | None = None) -> dict:
	"""One class in Moodle: its course, its users, their enrolments. Records the outcome on the class."""
	client = client or MoodleClient.from_settings()
	group = frappe.get_doc("Student Group", group_name)
	s = settings()
	try:
		course_id = _ensure_course(client, group)
		enrolled = client.call("core_enrol_get_enrolled_users", courseid=course_id) or []
		present = {u["id"] for u in enrolled}

		wanted_students, enrol = set(), []
		for row in group.students:
			if not row.active:
				continue
			user = _student_user(client, row.student)
			if user:
				wanted_students.add(user)
				if user not in present:
					enrol.append({"roleid": s.student_role_id or 5, "userid": user, "courseid": course_id})
		for row in group.instructors:
			user = _lecturer_user(client, row.instructor)
			if user and user not in present:
				enrol.append({"roleid": s.teacher_role_id or 3, "userid": user, "courseid": course_id})
		if enrol:
			client.call("enrol_manual_enrol_users", enrolments=enrol)

		# students who left the class: unenrolled (lecturers are left to Moodle's own course settings)
		student_role = s.student_role_id or 5
		leaving = [
			{"userid": u["id"], "courseid": course_id}
			for u in enrolled
			if u["id"] not in wanted_students and any(r.get("roleid") == student_role for r in u.get("roles") or [])
		]
		if leaving:
			client.call("enrol_manual_unenrol_users", enrolments=leaving)

		frappe.db.set_value(
			"Student Group",
			group.name,
			{"educore_moodle_course_id": course_id, "educore_moodle_synced_on": now_datetime(), "educore_moodle_error": None},
			update_modified=False,
		)
		return {"class": group.name, "course_id": course_id, "enrolled": len(enrol), "unenrolled": len(leaving)}
	except (MoodleError, requests.RequestException) as e:
		frappe.db.set_value("Student Group", group.name, "educore_moodle_error", str(e)[:1000], update_modified=False)
		return {"class": group.name, "error": str(e)}


def sync_all() -> dict:
	"""Scheduled hourly, and on demand: every active class of the current years, if Moodle is connected"""
	s = settings()
	if not s.moodle_enabled:
		return {"skipped": True}
	client = MoodleClient.from_settings()
	years = sorted(set(frappe.get_all("Student Group", filters={"group_based_on": "Course", "disabled": 0}, pluck="academic_year")), reverse=True)[:2]
	results = [
		sync_class(name, client)
		for name in frappe.get_all(
			"Student Group", filters={"group_based_on": "Course", "disabled": 0, "academic_year": ("in", years or [""])}, pluck="name"
		)
	]
	failed = [r for r in results if r.get("error")]
	summary = _("{0} classes synced, {1} failed").format(len(results) - len(failed), len(failed))
	frappe.db.set_single_value("Learning Platform Settings", {"last_sync_on": now_datetime(), "last_sync_result": summary})
	return {"synced": len(results) - len(failed), "failed": len(failed), "results": results}


def test_connection(url: str | None = None, token: str | None = None) -> dict:
	"""Moodle's site information, to confirm the address and token work"""
	client = MoodleClient(url, token) if url and token else MoodleClient.from_settings()
	info = client.call("core_webservice_get_site_info")
	return {"site": info.get("sitename"), "release": info.get("release"), "user": info.get("username")}
