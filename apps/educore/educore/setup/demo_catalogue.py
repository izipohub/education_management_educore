"""EduCore Demo University's programmes, courses and programme offerings (development only).

Called by educore.setup.demo.create_demo_university. Adds whatever is missing; changes nothing else.
"""

import frappe

#: code, name, unit code, credits, NQF level
COURSES = [
	("CMP1511", "Programming Fundamentals", "COMP", 16, 5),
	("CMP1521", "Computer Systems", "COMP", 16, 5),
	("CMP2511", "Data Structures and Algorithms", "COMP", 16, 6),
	("CMP2521", "Databases", "COMP", 16, 6),
	("MAT1511", "Calculus I", "MATH", 16, 5),
	("STA1511", "Introduction to Statistics", "MATH", 16, 5),
	("MAT2511", "Linear Algebra", "MATH", 16, 6),
	("ACC1511", "Financial Accounting I", "ACCF", 16, 5),
	("ACC1521", "Cost and Management Accounting", "ACCF", 16, 5),
	("FIN2511", "Corporate Finance", "ACCF", 16, 6),
	("MGT1511", "Principles of Management", "MGMT", 16, 5),
	("ECO1511", "Microeconomics", "MGMT", 16, 5),
	("MGT2511", "Organisational Behaviour", "MGMT", 16, 6),
	("EDU1511", "Foundations of Education", "EDFN", 16, 5),
	("EDU1521", "Educational Psychology", "EDFN", 16, 5),
	("EDU2511", "Curriculum and Instruction", "EDFN", 16, 6),
	("NUR1511", "Fundamentals of Nursing", "NURS", 16, 5),
	("ANA1511", "Anatomy and Physiology", "NURS", 16, 5),
	("NUR2511", "Community Health Nursing", "NURS", 16, 6),
	("MBA9511", "Strategic Management", "MGMT", 20, 9),
	("MBA9521", "Financial Management for Managers", "MGMT", 20, 9),
	("MBA9531", "Research Methods", "MGMT", 20, 9),
]

#: code, name, unit code, qualification, NQF level, credits, years, courses, offerings (campus, mode)
PROGRAMMES = [
	(
		"BCS", "Bachelor of Computer Science", "COMP", "Bachelor's Degree", 7, 360, 3,
		["CMP1511", "CMP1521", "MAT1511", "CMP2511", "CMP2521"],
		[("WHK", "Full-time"), ("OSH", "Full-time")],
	),
	(
		"DIT", "Diploma in Information Technology", "COMP", "Diploma", 6, 360, 3,
		["CMP1511", "CMP1521", "CMP2521"],
		[("OSH", "Full-time"), ("WHK", "Part-time")],
	),
	(
		"BSAMS", "Bachelor of Science in Applied Mathematics and Statistics", "MATH", "Bachelor's Degree", 7, 360, 3,
		["MAT1511", "STA1511", "MAT2511", "CMP1511"],
		[("WHK", "Full-time")],
	),
	(
		"BACC", "Bachelor of Accounting", "ACCF", "Bachelor's Degree", 7, 360, 3,
		["ACC1511", "ACC1521", "ECO1511", "STA1511", "FIN2511"],
		[("WHK", "Full-time"), ("OSH", "Full-time"), ("KMP", "Part-time")],
	),
	(
		"DAF", "Diploma in Accounting and Finance", "ACCF", "Diploma", 6, 360, 3,
		["ACC1511", "ACC1521", "ECO1511"],
		[("KMP", "Full-time"), ("WHK", "Distance")],
	),
	(
		"BBA", "Bachelor of Business Administration", "MGMT", "Bachelor's Degree", 7, 360, 3,
		["MGT1511", "ECO1511", "ACC1511", "MGT2511"],
		[("WHK", "Full-time"), ("KMP", "Part-time")],
	),
	(
		"BEDP", "Bachelor of Education (Primary)", "EDFN", "Honours Degree", 8, 480, 4,
		["EDU1511", "EDU1521", "EDU2511"],
		[("WHK", "Full-time"), ("OSH", "Full-time")],
	),
	(
		"BNS", "Bachelor of Nursing Science", "NURS", "Honours Degree", 8, 480, 4,
		["NUR1511", "ANA1511", "NUR2511"],
		[("WHK", "Full-time")],
	),
	(
		"MBA", "Master of Business Administration", "MGMT", "Master's Degree", 9, 240, 2,
		["MBA9511", "MBA9521", "MBA9531"],
		[("WHK", "Part-time")],
	),
]

#: postgraduate programmes: code: (minimum NQF level of the prior qualification, minimum average %)
POSTGRADUATE = {"MBA": (7, 60)}


#: First-year places per intake, by mode, with exceptions per (programme, campus)
INTAKE_CAPACITY_BY_MODE = {"Full-time": 60, "Part-time": 30, "Distance": 100, "Blended": 40}
INTAKE_CAPACITY = {
	("BNS", "WHK"): 30,  # clinical placements limit nursing
	("BCS", "OSH"): 40,
	# tiny, so the capacity rule can be tried by hand: two places, both taken in the demo data
	("BSAMS", "WHK"): 2,
	("MBA", "WHK"): 25,
}


def _unit(code):
	return frappe.db.get_value("Department", {"educore_unit_code": code})


def _campus(code):
	return frappe.db.get_value("Campus", {"campus_code": code})


def create_catalogue() -> dict:
	course_by_code = {}
	for code, name, unit, credits, level in COURSES:
		existing = frappe.db.get_value("Course", {"educore_course_code": code})
		if not existing:
			existing = (
				frappe.get_doc(
					{
						"doctype": "Course",
						"course_name": name,
						"educore_course_code": code,
						"department": _unit(unit),
						"educore_credits": credits,
						"educore_nqf_level": level,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		course_by_code[code] = existing

	offerings = 0
	for code, name, unit, qualification, level, credits, years, courses, campus_modes in PROGRAMMES:
		program = frappe.db.get_value("Program", {"educore_programme_code": code})
		if not program:
			program = (
				frappe.get_doc(
					{
						"doctype": "Program",
						"program_name": name,
						"program_abbreviation": code,
						"educore_programme_code": code,
						"department": _unit(unit),
						"educore_qualification_type": qualification,
						"educore_nqf_level": level,
						"educore_credits": credits,
						"educore_duration_years": years,
						"educore_study_level": "Postgraduate" if code in POSTGRADUATE else "Undergraduate",
						"educore_min_prior_nqf": POSTGRADUATE.get(code, (None, None))[0],
						"educore_min_prior_average": POSTGRADUATE.get(code, (None, None))[1],
						"courses": [
							{"course": course_by_code[c], "course_name": course_by_code[c], "required": 1}
							for c in courses
						],
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		for campus_code, mode in campus_modes:
			campus = _campus(campus_code)
			filters = {"program": program, "campus": campus, "mode_of_study": mode}
			capacity = INTAKE_CAPACITY.get((code, campus_code), INTAKE_CAPACITY_BY_MODE[mode])
			existing = frappe.db.get_value("Programme Offering", filters)
			if not existing:
				frappe.get_doc({"doctype": "Programme Offering", **filters, "intake_capacity": capacity}).insert(
					ignore_permissions=True
				)
			elif not frappe.db.get_value("Programme Offering", existing, "intake_capacity"):
				frappe.db.set_value("Programme Offering", existing, "intake_capacity", capacity)
			offerings += 1

	return {"courses": len(COURSES), "programmes": len(PROGRAMMES), "offerings": offerings}
