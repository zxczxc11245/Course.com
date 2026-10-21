# Course.com

#### Video Demo: <https://youtu.be/h5ZY52qHp_U>

#### Description:

Course.com is a full-stack web application built with Flask (Python), SQLite, HTML, CSS, and JavaScript that simulates a simple online course-selling platform. The idea behind the project is to take the core concepts taught throughout CS50 — web development with Flask, relational databases with SQL, server-side templating with Jinja, client-side interactivity with JavaScript, and secure handling of user accounts — and combine them into one coherent, working product rather than a set of disconnected exercises.

The platform lets a visitor browse a catalog of courses on the homepage, create an account, log in securely, "enroll" (purchase) in any course, and then revisit their personal account page to see exactly which courses they are enrolled in, with a direct link back into each one. Every piece of dynamic data on the site — the course catalog, the logged-in state of the header, and the list of enrolled courses on the account page — is pulled live from a SQLite database rather than being hardcoded, which was one of the central design goals of the project: nothing the user sees should be static once an account and enrollments exist.

I chose this project over the suggested distinct-category apps because it let me practice something I found more valuable for my own career direction (I am a cybersecurity student): building an authentication system from the ground up, correctly, including password hashing, session management, and the common mistakes that happen along the way when a beginner first implements login/logout logic (a mistake I made and fixed during development is documented below, because I think it is genuinely useful to explain, not just to hide).

## How the project works, page by page

**Home page (`/index.html`)** — Queries the `courses` table and renders every course as a card (image, title, short description, and a "More details" link). This is the entry point for both logged-in and logged-out visitors. The header changes dynamically depending on whether `session['user']` is set: a logged-out visitor sees "login" and "signup" buttons, while a logged-in visitor sees their profile picture (linking to their account page) and a "logout" button. This logic lives in every template that shares the header (`index.html`, `k1.html` through `k4.html`) through the same Jinja `{% if session.get('user') %}` block, since Flask's `session` object is automatically available inside every template without needing to be passed manually from each route.

**Course detail pages (`/course/<int:course_id>`)** — Each course has its own dedicated page (`k1.html` through `k4.html`), containing an autoplaying muted preview video, a full description, a "What will you learn?" list, and a "Buy now" button. The route itself is intentionally simple: it renders `k{course_id}.html` directly, which works because the four static template files were built to mirror the four rows seeded in the `courses` table one-to-one (course id 1 → `k1.html`, id 2 → `k2.html`, and so on). This is a known simplification: the project does not scale automatically if more courses were added through an admin panel, because the detail pages are hand-built rather than generated from a single dynamic template. I made this trade-off deliberately for the scope of this project, and I explain how I would fix it in the "Possible improvements" section below.

**Signup (`/signup`)** — Accepts a username and password (with a confirmation field), checks that the two passwords match and that the username is not already taken, hashes the password with Werkzeug's `generate_password_hash`, and inserts the new user into the `users` table. On success, the user is logged in immediately (their username is stored in the session) and redirected to the home page, rather than being sent back to the login page to re-enter their credentials a second time — a small UX decision aimed at reducing friction.

**Login (`/login`)** — Looks up the submitted username in the `users` table and uses `check_password_hash` to verify the submitted password against the stored hash. If both match, the username is stored in `session['user']` and the visitor is redirected home; otherwise an error message is rendered back on the same page. Passwords are never stored or compared in plain text anywhere in the codebase.

**Enroll (`/enroll/<int:course_id>`, POST only)** — This route is the heart of the project's relational design. It requires the visitor to be logged in (otherwise it redirects to `/login`), looks up the logged-in username's numeric `id` in the `users` table, and inserts a row into a dedicated `enrollments` table linking that `user_id` to the given `course_id`. The insert uses `INSERT OR IGNORE` together with a `UNIQUE(user_id, course_id)` constraint on the table, so that clicking "Buy now" twice on the same course never creates a duplicate enrollment or throws a database error — it simply does nothing the second time. This route is deliberately a `POST`-only endpoint (triggered by a plain HTML form with a single submit button, no JavaScript involved) because it changes server-side state, which is the correct semantic use of POST versus GET.

**Account (`/account`)** — Requires login. It performs a SQL `JOIN` between the `courses` and `enrollments` tables, filtered by the current user's numeric id, to fetch the full details (title, image, id) of every course that specific user has enrolled in — not just the raw, meaningless foreign key numbers stored in `enrollments`. If the user has no enrollments yet, a friendly empty-state message is shown instead of an empty grid. This page also displays the user's username and profile picture, and includes a "Change password" button (currently a placeholder link, intentionally left as a documented future feature — see below).

**Logout (`/logout`)** — Clears `session['user']` and redirects home.

## File structure

- `app.py` — All Flask routes and application logic. This is the single file containing every route (`/`, `/course/<id>`, `/signup`, `/login`, `/logout`, `/account`, `/enroll/<id>`), the `get_db_connection()` helper (opens a SQLite connection with `row_factory = sqlite3.Row` so query results can be accessed like dictionaries, e.g. `course["title"]`, instead of by positional index), and `init_db()`, which creates the `users` and `enrollments` tables on startup if they do not already exist.
- `init_db.py` — A standalone, one-time setup script that creates the `courses` table and seeds it with four fixed courses (Introduction to Programming, Python language, Web development, Encryption). It is run manually, separately from `app.py`, specifically because course data is treated as fixed "catalog" content rather than something the running application needs to regenerate on every restart — whereas `users` and `enrollments` genuinely do need to exist before the app can accept its first signup, so that logic lives inside `app.py` itself.
- `templates/` — All Jinja2 HTML templates: `index.html` (home/catalog), `login.html`, `signup.html`, `account.html`, and `k1.html`–`k4.html` (one detail page per course).
- `static/style.css` — A single hand-written stylesheet (no CSS framework) covering the whole site, organized into clearly labeled sections (Base, Header, Layout, Cards/Buttons, Login/Signup forms, User box, Account page) to keep nearly 500 lines of CSS navigable.
- `static/ph1.jfif` — Placeholder profile picture shown for every logged-in user.
- `static/v/` — The four autoplaying preview videos shown on each course's detail page.
- `.gitignore` — Excludes `database.db`, `__pycache__/`, and `*.pyc` from version control. The database file is deliberately never committed, because it is runtime-generated state (and, during development, contained real — if test — account credentials), not source code.

## How to run it

1. Install dependencies: `pip install flask werkzeug`
2. Run the one-time catalog setup: `python init_db.py` (creates `database.db` and seeds the four courses — this also implicitly creates the file that `app.py`'s own `init_db()` function will then add the `users` and `enrollments` tables into)
3. Start the server: `python app.py`
4. Visit `http://127.0.0.1:5000` in a browser

## Design decisions and challenges

**The `session['user']` bug.** Early in development, the login route had a bug where it set `session["user"] = username` and then, on the very next line, overwrote it with `session["user"] = password` — meaning every logged-in session actually stored the user's *password* instead of their username, with no real authentication check against the database at all. I'm documenting this because fixing it (separating the two assignments, adding a real `check_password_hash` comparison, and only setting the session after that check passes) was the point where the authentication system became genuinely secure rather than just visually functional, and I think that distinction matters more than the bug itself.

**The duplicate `return` bug in `/account`.** At one point, the `account()` view function contained a first, premature `return render_template(...)` that did not pass the enrolled courses to the template, followed by dead code below it (including a second, correct `return` with the `courses` query) that could never execute, because a function exits immediately at its first `return` statement. This meant the "My Courses" section silently never rendered any courses, with no error thrown anywhere, which made it a genuinely tricky bug to spot — a good reminder that Flask (and Python generally) will not warn about unreachable code by default.

**Why a separate `enrollments` table instead of a column on `users`.** A user can enroll in more than one course, and a course can have more than one enrolled user, which is a many-to-many relationship. Storing enrollments as, say, a comma-separated list of course ids on the `users` table would have been simpler to write initially but would make querying, enforcing uniqueness, and maintaining referential integrity significantly harder. A dedicated junction table with a `UNIQUE(user_id, course_id)` constraint and foreign keys is the standard relational solution, and implementing it was a deliberate choice to practice proper database normalization rather than taking a shortcut.

**Why course detail pages are static files mapped by id instead of one dynamic template.** This was a scope trade-off. A more "correct" long-term design would be a single `course_detail.html` template that pulls its video URL, title, and description straight from the `courses` table, the same way `index.html` already does for the catalog cards. I built the four pages as separate files instead because each one needed slightly different, hand-written long-form content (the "What will you learn?" lists differ meaningfully course to course), and templating that cleanly was secondary to getting the core authentication/enrollment system working correctly within the project's time scope.

## Possible improvements (not implemented, by choice)

- Make `/course/<id>` pull all content dynamically from the `courses` table (adding `video_url` and a `what_you_will_learn` field to the schema) instead of relying on four hardcoded template files, so new courses could be added through the database alone.
- Implement the "Change password" button on the account page, which is currently a visible but non-functional placeholder.
- Validate that a requested `course_id` actually exists before rendering its page, to avoid a server error on an invalid URL instead of a friendly "not found" message.
- Move `app.secret_key` out of the source code and into an environment variable before any real deployment, since it is currently hardcoded for local development convenience only.