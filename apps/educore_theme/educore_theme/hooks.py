app_name = "educore_theme"
app_title = "EduCore Theme"
app_publisher = "Izipo"
app_description = "EduCore look for Frappe: login page, logos, favicon and colours, overridable per university"
app_email = "dev@izipo.health"
app_license = "GNU General Public License (v3)"

# No add_to_apps_screen: a theme is not an app people open.

# The login (and forgot-password) page and the /apps screen are website pages
web_include_css = ["/assets/educore_theme/css/educore-web.css"]
web_include_js = ["/assets/educore_theme/js/educore-web.js"]
# The university's colours, icons and login text, from EduCore Branding (or EduCore's defaults)
update_website_context = ["educore_theme.branding.website_context"]

# Used only where Website and Navbar Settings name no logo of their own (branding.apply fills them)
app_logo_url = "/assets/educore_theme/images/educore-logo.svg"

after_install = "educore_theme.branding.apply"
after_migrate = "educore_theme.branding.apply"

# ERPNext's and Frappe's logos in the desk's app switcher and sidebar become the brand's icon
boot_session = "educore_theme.branding.boot_session"
