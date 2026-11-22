# EduCore Theme

The EduCore look for Frappe 16 and ERPNext, with each university's own brand on top:

- **Login page** (and forgot password): a hero column beside a glass sign-in card on a dark backdrop, the
  layout of the Izipo Consulting workspace login. Inter is served from the app, so it works on a campus
  network with no internet.
- **EduCore Branding** (settings, System Manager): the university's name, logos (normal, on-dark, icon,
  favicon), three colours, and the login heading, text, highlights and optional background photo. Every
  empty field uses the EduCore default, so a new installation is branded EduCore out of the box.
- **Name, logo, favicon and splash** in Website, Navbar and System Settings, written on install, on every
  migrate and when EduCore Branding is saved. Anything an administrator set to their own value there is
  left alone.
- **ERPNext's and Frappe's logos** in the desk's app switcher and sidebar, and on the `/apps` screen, become
  the brand's icon. Frappe HR and Education keep their own icons, so their tiles stay distinguishable.

Colours reach the pages as CSS variables (`--edu-primary`, `--edu-accent`, `--edu-night`, plus
`--edu-on-accent`, chosen for contrast), set per site by `branding.website_context()`; the stylesheet never
needs editing for a new university.

## Install

In the EduCore development stack this app is installed automatically (see `docker/frappe/init.sh`).
Elsewhere:

```
bench get-app educore_theme /path/to/apps/educore_theme
bench --site <site> install-app educore_theme
bench build --app educore_theme
```

Requires `frappe` 16.

## Tests

```
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app educore_theme
```

## Brand assets

The EduCore logo and icon in `educore_theme/public/images` are placeholders (navy `#13306B`/`#0B1F3A`
and gold `#F2B33D`), to be replaced by the final EduCore brand. Inter is under the SIL Open Font License
(`public/fonts/Inter-LICENSE.txt`).

## License

GNU General Public License (v3). See `license.txt`.
