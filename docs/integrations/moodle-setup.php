<?php
// Sets up Moodle for EduCore: a dedicated user and role, a web service limited to the functions EduCore calls, and
// a token. Run it once on the Moodle server, from Moodle's directory, as the web server's user:
//
//   cd /path/to/moodle && sudo -u www-data php /path/to/moodle-setup.php --password='a strong password for the educore user'
//
// Running it again changes nothing (it adds only what is missing) and prints the same token. Give the token, with
// Moodle's address, to EduCore's Integrations screen. See docs/integrations/moodle.md.
//
// Single sign-on (people sign in to Moodle with EduCore): once "Single sign-on" is chosen on EduCore's Integrations
// screen, run it again with the three values that screen shows:
//
//   ... --password='...' --sso-url='https://educore.example.edu' --sso-client-id='...' --sso-client-secret='...'
//
// It adds "EduCore" to Moodle's login page (OAuth 2, no email confirmation: EduCore is the university's own sign-in),
// matching people to their accounts by email, and switches on Moodle's OAuth 2 authentication.
define('CLI_SCRIPT', true);
require(getcwd() . '/config.php');
require_once($CFG->libdir . '/clilib.php');
[$options] = cli_get_params(['password' => '', 'sso-url' => '', 'sso-client-id' => '', 'sso-client-secret' => '']);
if (!$options['password']) {
  cli_error("Give the educore user's password: --password='...'");
}
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->libdir . '/externallib.php');

set_config('enablewebservices', 1);
set_config('webserviceprotocols', 'rest');

$functions = [
  'core_webservice_get_site_info', 'core_user_get_users_by_field', 'core_user_create_users', 'core_user_update_users',
  'core_course_get_categories', 'core_course_create_categories', 'core_course_get_courses_by_field',
  'core_course_create_courses', 'core_enrol_get_enrolled_users', 'enrol_manual_enrol_users',
  'enrol_manual_unenrol_users', 'core_course_get_contents', 'gradereport_user_get_grade_items',
];
$caps = [
  'webservice/rest:use', 'moodle/user:create', 'moodle/user:update', 'moodle/user:viewdetails', 'moodle/user:viewalldetails',
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

// --- single sign-on with EduCore -----------------------------------------------------------------------------
if ($options['sso-url']) {
  if (!$options['sso-client-id'] || !$options['sso-client-secret']) {
    cli_error('Give --sso-client-id and --sso-client-secret too, from EduCore\'s Integrations screen');
  }
  // Moodle's OAuth 2 settings are the site administrator's: act as them, as Moodle's own command-line tools do
  \core\session\manager::set_user(get_admin());
  $base = rtrim($options['sso-url'], '/');
  $fields = [
    'name' => 'EduCore', 'clientid' => $options['sso-client-id'], 'clientsecret' => $options['sso-client-secret'],
    'baseurl' => '', 'loginscopes' => 'openid profile email', 'loginscopesoffline' => 'openid profile email',
    'loginparams' => '', 'loginparamsoffline' => '', 'alloweddomains' => '', 'image' => '',
    'showonloginpage' => \core\oauth2\issuer::LOGINONLY, 'requireconfirmation' => 0, 'basicauth' => 0, 'enabled' => 1,
  ];
  $issuer = \core\oauth2\issuer::get_record(['name' => 'EduCore']);
  if ($issuer) {
    foreach ($fields as $k => $v) { $issuer->set($k, $v); }
    $issuer->update();
  } else {
    $issuer = \core\oauth2\api::create_issuer((object)$fields);
  }
  $endpoints = [
    'authorization_endpoint' => '/api/method/frappe.integrations.oauth2.authorize',
    'token_endpoint' => '/api/method/frappe.integrations.oauth2.get_token',
    'userinfo_endpoint' => '/api/method/frappe.integrations.oauth2.openid_profile',
  ];
  foreach ($endpoints as $name => $path) {
    $endpoint = \core\oauth2\endpoint::get_record(['issuerid' => $issuer->get('id'), 'name' => $name]);
    if ($endpoint) {
      $endpoint->set('url', $base . $path);
      $endpoint->update();
    } else {
      \core\oauth2\api::create_endpoint((object)['issuerid' => $issuer->get('id'), 'name' => $name, 'url' => $base . $path]);
    }
  }
  // what EduCore says about the person: its stable identifier keys the link, the email finds the account the sync made
  $mapping = ['sub' => 'username', 'email' => 'email', 'given_name' => 'firstname', 'family_name' => 'lastname'];
  foreach ($mapping as $external => $internal) {
    if (!\core\oauth2\user_field_mapping::get_record(['issuerid' => $issuer->get('id'), 'externalfield' => $external])) {
      \core\oauth2\api::create_user_field_mapping((object)['issuerid' => $issuer->get('id'), 'externalfield' => $external, 'internalfield' => $internal]);
    }
  }
  $auths = array_filter(explode(',', $CFG->auth ?? ''));
  if (!in_array('oauth2', $auths)) {
    $auths[] = 'oauth2';
    set_config('auth', implode(',', $auths));
    \core_plugin_manager::reset_caches();
  }
  echo "SINGLE SIGN-ON: 'EduCore' is on Moodle's login page\n";
}
