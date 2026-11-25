app_name = "educore"
app_title = "EduCore"
app_publisher = "Izipo"
app_description = "University management on Frappe: institution, academics, students, finance, HR and campus"
app_email = "dev@izipo.health"
app_license = "GNU General Public License (v3)"

required_apps = ["erpnext", "hrms", "education"]

# Custom fields on upstream DocTypes (educore/setup/custom_fields.py), and roles and positions
# (educore/access/roles.py), kept as defined
after_install = "educore.setup.install.after_migrate"
after_migrate = "educore.setup.install.after_migrate"

# Students and guardians see only their own (their wards') enrolments and fee invoices, as Education
# does for Student; staff are unaffected
permission_query_conditions = {
	"Program Enrollment": "educore.academics.student_access.query_conditions",
	"Sales Invoice": "educore.academics.student_access.query_conditions",
}
has_permission = {
	"Program Enrollment": "educore.academics.student_access.has_permission",
	"Sales Invoice": "educore.academics.student_access.has_permission",
}

scheduler_events = {
	# application fees paid by EFT: match the imported bank statement to applications
	# and student fees, by student number
	"hourly": [
		"educore.admissions.fees.match_bank_transactions",
		"educore.finance.student_payments.match_bank_transactions",
		# and sponsors' payments, by sponsor number
		"educore.finance.sponsors.match_bank_transactions",
		# classes, students and lecturers kept in Moodle, once ICT connects it
		"educore.learning.moodle.sync_all",
	],
	# offers: reminders before the deadline, and unanswered offers lapse
	"daily": ["educore.admissions.offers.daily"],
}

# Only back-office positions (Desk Access) and System Managers open the Desk; others go to the Vue app
before_request = ["educore.access.desk.redirect_from_desk"]
get_website_user_home_page = "educore.access.desk.website_user_home_page"

# class attendance without a holiday list, and a friendlier holiday message (educore.academics.attendance)
override_doctype_class = {"Student Attendance": "educore.academics.attendance.StudentAttendance"}

doc_events = {
	# Desk users get the back-office Module Profile; lecturers get their Instructor record
	"User": {
		"validate": "educore.access.desk.assign_module_profile",
		"on_update": "educore.academics.lecturers.on_user_update",
	},
	"User Permission": {"after_insert": "educore.academics.lecturers.on_user_permission_change"},
	"Employee": {"on_update": "educore.academics.lecturers.on_employee_update"},
	# Faculties, schools and departments live in ERPNext's Department tree
	"Department": {"validate": "educore.institution.department.validate"},
	# Programmes and courses belong to academic units, with codes, credits and NQF levels
	"Program": {"validate": "educore.academics.catalogue.validate_program"},
	"Course": {"validate": "educore.academics.catalogue.validate_course"},
	# Applicants, students and enrolments are on a programme offering: campus, mode, faculty
	"Student Applicant": {
		"validate": "educore.academics.students.validate_applicant",
		"on_update": "educore.admissions.notify.on_applicant_update",
	},
	"Student": {"validate": "educore.academics.students.validate_student"},
	"Program Enrollment": {
		"validate": "educore.academics.students.validate_enrollment",
		"on_submit": "educore.academics.students.on_enrollment_submit",
	},
	# Student fees per offering, invoiced on enrolment to the campus cost center
	"Fee Structure": {
		"validate": "educore.finance.student_fees.validate_fee_structure",
		"before_submit": "educore.finance.student_fees.before_submit_fee_structure",
	},
	"Payment Entry": {"validate": "educore.finance.student_fees.validate_payment"},
}
