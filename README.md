# EduCore

University management on Frappe 16, ERPNext, Frappe HR and Frappe Education: one installation per
university, many campuses. Architecture, decisions and the roadmap are in [AGENT.md](AGENT.md).

## Repository

| Path | What |
|---|---|
| `apps/educore` | The EduCore Frappe app: institution (campuses, faculties), academics (programmes, offerings, admissions, enrolment), student fees, roles and positions |
| `apps/educore_theme` | Login page, logos and colours; each university can override them in EduCore Branding |
| `docker/frappe` | Development stack: Frappe 16 bench with ERPNext, HRMS, Education and the apps above |
| `docs/` | Architecture notes, such as roles and positions |

## Development

The stack sits behind Nginx Proxy Manager on the external Docker network `proxy` and publishes no ports.

```
cd docker/frappe
docker compose up -d            # first start builds the bench: slow, downloads several GB
docker compose logs -f frappe
```

Add an NPM proxy host for `educore.localhost` → `educore-frappe:8000` (websockets on, with a custom location
`/socket.io` → `educore-frappe:9000`), then open http://educore.localhost.

The apps in `apps/` are linked into the bench and installed on start; edits are live (restart the `frappe`
container for Python changes, and run `bench clear-cache` after changing hooks).

Demo data, on a development site only (`*.localhost`):

```
docker compose exec frappe bash -lc 'cd frappe-bench && \
  bench --site educore.localhost execute educore.setup.demo.create_demo_university && \
  bench --site educore.localhost execute educore.access.demo_users.create && \
  bench --site educore.localhost execute educore.access.test_users.create && \
  bench --site educore.localhost execute educore.setup.demo_students.create'
```

Development logins are kept in a local, git-ignored `CREDS.md`.

## Tests

```
docker compose exec frappe bash -lc 'cd frappe-bench && \
  bench --site educore.localhost run-tests --app educore && \
  bench --site educore.localhost run-tests --app educore_theme'
```
