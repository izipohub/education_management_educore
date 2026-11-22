# EduCore

University management on Frappe 16, ERPNext, Frappe HR and Frappe Education: one installation per
university, many campuses. Architecture, decisions and the roadmap are in [AGENT.md](AGENT.md).

## Repository

| Path | What |
|---|---|
| `apps/educore` | The EduCore Frappe app: institution (campuses, faculties), academics (programmes, offerings, admissions, enrolment), student fees, roles and positions |
| `apps/educore_theme` | Login page, logos and colours; each university can override them in EduCore Branding |
| `frontend/educore-ui` | The Vue app every university user works in (Vue 3, TypeScript, Vite, PrimeVue 4.5.5, Tailwind) |
| `docker/frappe` | Development stack: Frappe 16 bench with ERPNext, HRMS, Education and the apps above |
| `docker/frontend` | The Vue app's Vite dev server, forwarding Frappe's paths to the bench |
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

### Vue app

```
cd docker/frontend
docker compose up -d            # Vite with hot reload; needs the Frappe stack running
```

Add an NPM proxy host for `app.educore.localhost` → `educore-ui:5173` with websockets on, then open
http://app.educore.localhost. Vite forwards `/api`, `/assets`, `/files` and `/socket.io` to Frappe, so the app
and Frappe share one origin and Frappe's session cookie works.

On the host: `cd frontend/educore-ui && npm ci && npm test` (Vitest), `npm run typecheck`, `npm run build`.
Browser tests against the running stack and its demo data (installed Google Chrome): `npm run e2e`.

Set the site's `educore_app_url` (`bench --site educore.localhost set-config educore_app_url
http://app.educore.localhost`): users without Desk access who open `/desk` are sent there. Only back-office
positions and System Managers use the Desk (AGENT.md 3.1).

## Tests

```
docker compose exec frappe bash -lc 'cd frappe-bench && \
  bench --site educore.localhost run-tests --app educore && \
  bench --site educore.localhost run-tests --app educore_theme'
```
