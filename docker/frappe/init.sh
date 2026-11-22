#!/bin/bash
# First start: a bench on version 16 with ERPNext, Frappe HR and Frappe Education, site educore.localhost.
# Every start: EduCore's own apps (the repository's apps/ folder, mounted at /home/frappe/educore-apps) are
# linked into the bench and installed on the site if they are not yet, then the bench runs.
set -e
SITE=educore.localhost
DB_ROOT_PASSWORD="${EDUCORE_DB_ROOT_PASSWORD:-educore}"
LOCAL_APPS_DIR=/home/frappe/educore-apps
# Version 16 needs Node 24 and Python 3.14, both in the bench image
NODE24=$(ls -d "${NVM_DIR}"/versions/node/v24* | tail -1)
export PATH="${NODE24}/bin:${PATH}"
PY314=$(ls -d "${HOME}"/.pyenv/versions/3.14*/bin/python3 | tail -1)

setup_bench() {
	cd /home/frappe
	[ -d frappe-bench/apps/frappe ] || bench init --skip-redis-config-generation --frappe-branch version-16 --python "${PY314}" frappe-bench
	cd frappe-bench
	bench set-mariadb-host mariadb
	bench set-redis-cache-host redis://redis:6379
	bench set-redis-queue-host redis://redis:6379
	bench set-redis-socketio-host redis://redis:6379
	sed -i '/redis/d;/watch/d' Procfile
	# The web process: gunicorn, as in production, not the development server (whose debugger must never
	# face the internet); application_with_statics() still serves /assets and /files without nginx
	sed -i 's#^web: .*#web: cd sites \&\& ../env/bin/gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 "frappe.app:application_with_statics()"#' Procfile
	# An app is listed in sites/apps.txt only after get-app finished; a half-fetched one is fetched again
	for app in erpnext hrms education; do
		if ! grep -qx "${app}" sites/apps.txt 2>/dev/null; then
			rm -rf "apps/${app}"
			bench get-app --branch version-16 "${app}"
		fi
	done
	[ -d "sites/${SITE}" ] || bench new-site "${SITE}" --mariadb-root-password "${DB_ROOT_PASSWORD}" --admin-password admin --no-mariadb-socket
	bench --site "${SITE}" install-app erpnext hrms education
	bench --site "${SITE}" enable-scheduler
	bench use "${SITE}"
	# Written only after the site is fully installed, so an interrupted first start resumes
	touch .educore-ready
}

# EduCore's apps are edited in the repository; the bench sees them through a link, so changes are live
# (Python on the next request after a restart, CSS/JS/images at once through the assets link)
install_local_apps() {
	cd /home/frappe/frappe-bench
	[ -d "${LOCAL_APPS_DIR}" ] || return 0
	local installed
	installed=$(bench --site "${SITE}" list-apps 2>/dev/null | awk '{print $1}')
	for dir in "${LOCAL_APPS_DIR}"/*/; do
		local app
		app=$(basename "${dir}")
		[ -f "${dir}/pyproject.toml" ] && [ -f "${dir}/${app}/hooks.py" ] || continue
		[ -L "apps/${app}" ] || { rm -rf "apps/${app}"; ln -s "${dir%/}" "apps/${app}"; }
		if ! grep -qx "${app}" sites/apps.txt; then
			echo "Linking ${app}"
			uv pip install --quiet -e "apps/${app}" --python env/bin/python
			# Frappe writes apps.txt without a final newline; add one so the app gets its own line
			sed -i -e '$a\' sites/apps.txt
			echo "${app}" >> sites/apps.txt
		fi
		if [ -d "${dir}/${app}/public" ] && [ ! -e "sites/assets/${app}" ]; then
			bench build --app "${app}"
		fi
		if ! grep -qx "${app}" <<< "${installed}"; then
			echo "Installing ${app} on ${SITE}"
			bench --site "${SITE}" install-app "${app}"
		fi
	done
}

[ -f /home/frappe/frappe-bench/.educore-ready ] || setup_bench
install_local_apps
cd /home/frappe/frappe-bench && exec bench start
