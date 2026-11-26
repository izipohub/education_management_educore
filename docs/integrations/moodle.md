# Connecting Moodle

For the university's ICT administrators. EduCore keeps Moodle in step with its classes and reads the grades of
online assessments. Moodle stays where learning happens; EduCore stays the official record of results.

Tested with Moodle 4.5.

## What EduCore does in Moodle

| When | What | Through |
|---|---|---|
| Every hour, and on demand (Integrations, Sync now) | Each class of the current years becomes a Moodle course (found by its ID number, the class's name), in its campus's category | Course and category functions |
| The same sync | Each student and lecturer gets a Moodle user (found by ID number: the student number, or the staff number), enrolled as student or teacher; students who leave a class are unenrolled | User and manual enrolment functions |
| When a lecturer links an online assessment | Lists the graded activities of the class's course (assignments, quizzes, workshops, lessons, H5P, external tools, SCORM) | `core_course_get_contents` |
| When a lecturer clicks From Moodle | Reads the activity's grades, scales them to what the assessment is marked out of, and shows them to the lecturer to check and save | `gradereport_user_get_grade_items` |

EduCore never changes grades in Moodle, and a grade read from Moodle counts only once the lecturer saves it and the
marks pass moderation and the examination board.

## Setting up (about ten minutes)

1. Copy [`moodle-setup.php`](moodle-setup.php) to the Moodle server and run it once from Moodle's directory, as
   the web server's user:

   ```
   cd /path/to/moodle
   sudo -u www-data php /path/to/moodle-setup.php --password='a strong password'
   ```

   It enables web services and REST, and creates:
   - a user `educore` (the password is for that user; nobody signs in with it);
   - a system role "EduCore web service" with only the capabilities listed below, allowed to assign the Student
     and Teacher roles;
   - an external service "EduCore" with only the functions listed below, restricted to the `educore` user;
   - a token for it, printed as `TOKEN=...`.

   Running it again adds only what is missing and prints the same token. An activity type this Moodle does not
   have is left out, and named.

2. In EduCore, Integrations: give Moodle's address (as the EduCore server reaches it) and the token, then **Test
   connection**. It names any function the token's service does not allow.

3. Check the Student and Teacher role IDs on the same screen (5 and 3 on a standard Moodle), choose how people
   sign in to Moodle, and switch the connection on. The first sync runs within the hour, or press Sync now.

## Single sign-on

People sign in to Moodle with their EduCore login: Moodle's login page offers **EduCore**; someone already signed in
to EduCore goes straight in, anyone else signs in on EduCore's own login page first and comes back to Moodle.

1. In EduCore, Integrations: choose **Single sign-on** for "Sign-in on Moodle" and save. EduCore registers Moodle as
   a trusted sign-in client (no "allow access?" screen) and shows a **Single sign-on** panel with EduCore's
   address, a client ID and a client secret, and **Copy the command**.
2. On the Moodle server, run the setup script again with them:

   ```
   cd /path/to/moodle
   sudo -u www-data php /path/to/moodle-setup.php --password='...' \
     --sso-url='https://educore.university.edu' --sso-client-id='...' --sso-client-secret='...'
   ```

   It adds EduCore as an OAuth 2 service on Moodle's login page, with no email confirmation (EduCore is the
   university's own sign-in), maps EduCore's identifier, email and names to the Moodle account, and switches on
   Moodle's OAuth 2 authentication.
3. From the next sync, every account EduCore keeps in Moodle signs in with EduCore, including those made earlier with
   a Moodle password: they are switched over, and no longer asked to change a password.

Moodle matches a person to their account by email the first time, then by EduCore's own identifier for that login.

Two things Moodle requires:
- **https.** Moodle accepts a sign-in service only at an `https://` address; EduCore's address must be https.
- **Reaching EduCore from the Moodle server.** Moodle's server exchanges the sign-in code with EduCore. If EduCore's
  address resolves to a private address from the Moodle server (both on the university's network), Moodle blocks
  it by default: remove that address from Site administration, General, Security, HTTP security, "cURL blocked
  hosts list", and keep its port in "cURL allowed ports".

Choosing **Moodle password** again removes EduCore's sign-in client and ends the sessions it opened; the EduCore
button on Moodle's login page then stops working, so remove it there too (Site administration, Server, OAuth 2
services).

## What the token needs

**Functions** (the external service):
`core_webservice_get_site_info`, `core_user_get_users_by_field`, `core_user_create_users`, `core_user_update_users`,
`core_course_get_categories`, `core_course_create_categories`, `core_course_get_courses_by_field`,
`core_course_create_courses`, `core_enrol_get_enrolled_users`, `enrol_manual_enrol_users`,
`enrol_manual_unenrol_users`, `core_course_get_contents`, `gradereport_user_get_grade_items`.

**Capabilities** (the role, at system level):

| Capability | Why |
|---|---|
| `webservice/rest:use` | To call Moodle at all |
| `moodle/user:create`, `moodle/user:viewdetails`, `moodle/user:viewalldetails`, `moodle/site:viewuseridentity` | To find people by ID number and create those missing |
| `moodle/user:update` | With single sign-on: to switch accounts made earlier with a Moodle password to EduCore's sign-in |
| `moodle/course:create`, `moodle/category:manage`, `moodle/course:view`, `moodle/course:viewhiddencourses` | To find or create each class's course and its campus's category |
| `moodle/course:viewparticipants`, `moodle/course:enrolreview`, `enrol/manual:enrol`, `enrol/manual:unenrol`, `moodle/role:assign` | To enrol and unenrol (with the Student and Teacher roles allowed to be assigned) |
| `mod/assign:view`, `mod/quiz:view`, `mod/workshop:view`, `mod/lesson:view`, `mod/h5pactivity:view`, `mod/lti:view`, `mod/scorm:savetrack` | To see each type of graded activity; without one, activities of that type are silently missing from the list |
| `moodle/grade:viewall`, `gradereport/user:view` | To read the grades |
| `moodle/grade:viewhidden` | To read the grades of activities whose marks are not shown to students yet (a quiz often hides marks until it closes); without it, such grades are silently missing |

## When something does not work

| What the lecturer or ICT sees | Why, and what to do |
|---|---|
| Test connection names missing functions | Add them to the "EduCore" external service (Site administration, Server, Web services, External services, Functions), or run the setup script again |
| "This class is not in Moodle yet" | The sync has not reached it: wait for the hourly sync or press Sync now; a class whose sync failed shows the reason on Integrations and on its page in Teaching |
| The lecturer's activity is not in the list | It is of a type the role cannot view (add its `mod/...:view` capability), or not graded (a page or a file has no grade) |
| From Moodle brings in fewer scores than expected | Those students are not graded in Moodle yet, or their Moodle user has no ID number (it is set by the sync; users made by hand before it keep theirs empty). EduCore says how many are not graded |
| A grade appears in Moodle but not in EduCore | The activity's marks are hidden and the role lacks `moodle/grade:viewhidden` |
| "Could not upgrade OAuth 2 token" after signing in with EduCore | Moodle's server could not reach EduCore: check its address from the Moodle server, and Moodle's cURL blocked hosts and allowed ports (see Single sign-on) |
| Moodle asks someone who signed in with EduCore to change a password | Their account was made before single sign-on and the sync has not run since: press Sync now |
