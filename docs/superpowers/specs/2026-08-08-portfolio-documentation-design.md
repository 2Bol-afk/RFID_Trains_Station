# RFID Train Station Portfolio Documentation Design

## Goal

Present the RFID Train Station project as a credible software-engineering portfolio piece using the real application, a consistent visual identity, concise technical documentation, and reproducible demo screenshots. Graphify and generated code graphs are explicitly out of scope.

## Selected approach

Use an automated, locally seeded Django demo and a headless browser to capture the actual interface. This is preferred over manually supplied screenshots because dimensions and data can be kept consistent, and over designed mockups because the images honestly represent the implemented application.

If automated browser capture is unavailable, the fallback is to run the application locally and capture the same routes with an installed browser. Artificial UI mockups will not be substituted for real screenshots.

## Branding

The approved Contactless Rail logo is the primary project mark. The full-resolution source remains at `docs/assets/rfid-train-station-logo.png`.

Application use:

- Copy a web-facing version into Django's `cards/static/cards/images/` directory.
- Display a small mark beside “RFID Station” in the shared navbar.
- Display a larger mark in the home-page hero.
- Display the mark on the login page.
- Add a favicon reference using a suitably sized derivative.

Documentation use:

- Center the logo above the README title.
- Keep the existing repository badges directly below the introduction.
- Use the logo once; do not repeat it as decoration throughout the document.

The existing Bootstrap layout and navigation behavior will remain intact. Branding changes will use the logo's navy, teal, amber, and off-white palette only where needed for visual consistency.

## Screenshot set

Capture four real application views at a consistent desktop viewport, targeting 1440×900 or the nearest browser-supported size:

1. Home page — overview and role selection.
2. Passenger interface — card tap and station selection workflow.
3. Cashier interface — card purchase/reload management.
4. Admin dashboard — operational statistics and recent activity.

Screenshots will be stored under `docs/assets/screenshots/` with descriptive lowercase filenames. They must use synthetic demo users, cards, stations, names, and email addresses. No local secrets, browser chrome, developer tools, or real personal data may be visible.

The README will show a compact two-column screenshot gallery with short captions. Full-size images remain clickable.

## Documentation structure

### README

The README becomes the portfolio landing page:

1. Logo, project name, one-sentence value proposition, and badges.
2. Screenshot gallery.
3. Problem and solution.
4. Key features.
5. Architecture and tap-to-ride data flow.
6. Technology stack.
7. Local setup and demo-data instructions.
8. Roles and access matrix.
9. API summary with links to detailed documentation.
10. Hardware bridge usage.
11. Testing and production considerations.
12. Contributors and an explicit personal-contribution section if ownership details are available.
13. License information that matches the repository contents.

### Supporting documents

- `docs/ARCHITECTURE.md`: system context, component responsibilities, data model, and ride-charge sequence using Mermaid diagrams.
- `docs/API.md`: actual routes, HTTP methods, authentication requirements, request fields, and representative responses.
- `docs/HARDWARE.md`: serial-reader assumptions, bridge configuration, data flow, operation, and troubleshooting.

Documentation must describe existing behavior accurately. Known limitations discovered during validation will be stated rather than hidden or described as completed features.

## Setup and capture flow

1. Create an isolated Python virtual environment inside the repository.
2. Install the checked-in requirements.
3. Run Django system and migration checks.
4. Apply migrations to the ignored local SQLite database.
5. Seed only synthetic demo users, stations, fare categories, cards, and transactions.
6. Start the local development server bound to loopback.
7. Capture the approved routes with a headless browser.
8. Stop the server and inspect every screenshot before using it.

Generated runtime files such as the virtual environment, SQLite database, logs, and browser profiles remain untracked.

## Error handling and safety

- Dependency or browser installation failures will be reported rather than bypassed with fake screenshots.
- If the existing setup command cannot seed valid data, use Django's documented management interfaces or a narrowly scoped fixture containing synthetic data.
- Authentication failures will be diagnosed before capture; protected pages will not be replaced by screenshots of login errors.
- Existing unrelated user changes will not be overwritten.
- GitHub push happens only after local verification and commits are complete.

## Verification

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- Available automated tests
- Verify every referenced documentation link and image path exists.
- Visually inspect the home, passenger, cashier, admin, and login pages after branding changes.
- Visually inspect every captured screenshot for correct content and synthetic-only data.
- Run `git diff --check` before committing.
- Review the final commit and repository status before pushing.

## Out of scope

- Graphify outputs or generated knowledge graphs.
- A full UI redesign.
- Fabricated product mockups presented as application screenshots.
- Deployment of a public production instance.
- Unrelated business-logic or security refactoring unless it is required to run and document the approved demo safely.
