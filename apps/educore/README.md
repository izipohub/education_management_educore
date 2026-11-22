# EduCore

The custom Frappe app for EduCore: university-specific records, rules, workflows, integrations and APIs
on Frappe 16, ERPNext, Frappe HR and Frappe Education. See `AGENT.md` at the repository root.

So far:

- **Roles and positions** (`educore/access/roles.py`): EduCore's roles, and the university's positions as
  Role Profiles, synced after install and every migrate. See `docs/architecture/roles-and-positions.md`.
- **Demo users** for a development site, one per position:
  `bench --site educore.localhost execute educore.access.demo_users.create`

## Install

In the EduCore development stack this app is installed automatically (see `docker/frappe/init.sh`).
Elsewhere, after ERPNext, HRMS and Education:

```
bench get-app educore /path/to/apps/educore
bench --site <site> install-app educore
```

## Tests

```
bench --site <site> run-tests --app educore
```

## License

GNU General Public License (v3). See `license.txt`.
