<?php
// Sets up Moodle for EduCore: a dedicated user and role, a web service limited to the functions EduCore calls, and
// a token. Run it once on the Moodle server, from Moodle's directory, as the web server's user:
//
//   cd /path/to/moodle && sudo -u www-data php /path/to/moodle-setup.php --password='a strong password for the educore user'
//
// Running it again changes nothing (it adds only what is missing) and prints the same token. Give the token, with
// Moodle's address, to EduCore's Integrations screen. See docs/integrations/moodle.md.
define('CLI_SCRIPT', true);
require(getcwd() . '/config.php');
require_once($CFG->libdir . '/clilib.php');
[$options] = cli_get_params(['password' => '']);
if (!$options['password']) {
  cli_error("Give the educore user's password: --password='...'");
}
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->libdir . '/externallib.php');

set_config('enablewebservices', 1);
set_config('webserviceprotocols', 'rest');

$functions = [
  'core_webservice_get_site_info', 'core_user_get_users_by_field', 'core_user_create_users',
  'core_course_get_categories', 'core_course_create_categories', 'core_course_get_courses_by_field',
  'core_course_create_courses', 'core_enrol_get_enrolled_users', 'enrol_manual_enrol_users',
  'enrol_manual_unenrol_users', 'core_course_get_contents', 'gradereport_user_get_grade_items',
];
$caps = [
  'webservice/rest:use', 'moodle/user:create', 'moodle/user:viewdetails', 'moodle/user:viewalldetails',
  'moodle/site:viewuseridentity', 'moodle/course:create', 'moodle/category:manage', 'moodle/course:view',
  'moodle/course:viewhiddencourses', 'moodle/course:viewparticipants', 'moodle/course:enrolreview',
  'enrol/manual:enrol', 'enrol/manual:unenrol', 'moodle/role:assign', 'moodle/grade:viewall', 'moodle/grade:viewhidden', 'gradereport/user:view',
  // to see the graded activities EduCore links to (each type's view capability)
  'mod/assign:view', 'mod/quiz:view', 'mod/workshop:view', 'mod/lesson:view', 'mod/h5pactivity:view', 'mod/lti:view', 'mod/scorm:savetrack',
];

$user = $DB->get_record('user', ['username' => 'educore']);
if (!$user) {
  $id = user_create_user(['username' => 'educore', 'password' => $options['password'], 'firstname' => 'EduCore',
    'lastname' => 'Integration', 'email' => 'educore@localhost.invalid', 'auth' => 'manual', 'confirmed' => 1,
    'mnethostid' => $CFG->mnet_localhost_id]);
  $user = $DB->get_record('user', ['id' => $id]);
}
$context = context_system::instance();
$roleid = $DB->get_field('role', 'id', ['shortname' => 'educorews']);
if (!$roleid) {
  $roleid = create_role('EduCore web service', 'educorews', 'What EduCore needs to keep courses, users and enrolments in step and read grades');
  set_role_contextlevels($roleid, [CONTEXT_SYSTEM]);
}
foreach ($caps as $cap) {
  // an activity type this Moodle does not have (a plugin not installed) is left out
  if (!get_capability_info($cap)) {
    echo "Not on this Moodle, left out: $cap\n";
    continue;
  }
  assign_capability($cap, CAP_ALLOW, $roleid, $context->id, true);
}
// the roles EduCore enrols people with
foreach (['student', 'editingteacher'] as $shortname) {
  $target = $DB->get_field('role', 'id', ['shortname' => $shortname]);
  if (!$DB->record_exists('role_allow_assign', ['roleid' => $roleid, 'allowassign' => $target])) {
    core_role_set_assign_allowed($roleid, $target);
  }
}
role_assign($roleid, $user->id, $context->id);

$service = $DB->get_record('external_services', ['shortname' => 'educore']);
if (!$service) {
  $sid = $DB->insert_record('external_services', (object)['name' => 'EduCore', 'shortname' => 'educore', 'enabled' => 1,
    'restrictedusers' => 1, 'downloadfiles' => 0, 'uploadfiles' => 0, 'timecreated' => time()]);
  $service = $DB->get_record('external_services', ['id' => $sid]);
}
foreach ($functions as $f) {
  if (!$DB->record_exists('external_services_functions', ['externalserviceid' => $service->id, 'functionname' => $f])) {
    $DB->insert_record('external_services_functions', (object)['externalserviceid' => $service->id, 'functionname' => $f]);
  }
}
if (!$DB->record_exists('external_services_users', ['externalserviceid' => $service->id, 'userid' => $user->id])) {
  $DB->insert_record('external_services_users', (object)['externalserviceid' => $service->id, 'userid' => $user->id, 'timecreated' => time()]);
}
accesslib_clear_all_caches(true);
$token = $DB->get_field('external_tokens', 'token', ['externalserviceid' => $service->id, 'userid' => $user->id]);
if (!$token) {
  $token = \core_external\util::generate_token(EXTERNAL_TOKEN_PERMANENT, $service, $user->id, $context, 0, '');
}
echo "TOKEN=$token\n";
