# Homepage photo gallery — NESA Rwanda

The seven homepage photos are **real photographs** (not AI-generated) taken from the public
website of Rwanda's **National Examination and School Inspection Authority (NESA)**:
<https://www.nesa.gov.rw/>.

They show real Rwandan students, teachers, and education officials — which matches the
70Scholar mission far better than generic stock photography.

## Files in `static/images/`

| # | File | Caption shown | Source on nesa.gov.rw |
| --- | --- | --- | --- |
| 1 | `students-library.jpg` | Rwanda's students | `/fileadmin/user_upload/NESA/Background_Images/WEB_2026.jpeg` |
| 2 | `students-classroom.jpg` | In the classroom | `/fileadmin/user_upload/NESA/Background_Images/WEB_2026_6.jpeg` |
| 3 | `student-chalkboard.jpg` | Every scholar has a voice | `/fileadmin/user_upload/NESA/Background_Images/WEB_2026_2.jpeg` |
| 4 | `students-collaborating.jpg` | Learning together | `/fileadmin/user_upload/NESA/Background_Images/WEB_2026_4.jpeg` |
| 5 | `teacher-and-students.jpg` | Teachers who open doors | `/fileadmin/user_upload/NESA/Background_Images/WEB_2026_7.jpeg` |
| 6 | `official-with-student.jpg` | Leaders investing in learners | News: *MINEDUC yatangije Ibizamini bya Leta… 2025/2026* (`csm_HMnpSdOW4AAvCKJ_1d2b681752.jpg`) |
| 7 | `education-leaders.jpg` | National commitment | `/fileadmin/user_upload/NESA/Background_Images/WEB_2026_1_1.jpeg` |

Images were downloaded at 1600px/1000px, then resized to ≤1200px and optimised to ~90–170 KB
each so the page stays fast on mobile connections.

> ⚠️ **Copyright / permission.** These images are published on a Rwandan government website.
> They are credited to NESA on the homepage, but there is **no explicit open licence** stated on
> the site. Before using them on a commercial or high-traffic public site, contact
> **info@nesa.gov.rw** to request permission, or replace them with photos you own. This is
> especially important because the images show identifiable students (minors).

They are **not** photographs of Isomo Academy, Yale, ESCM, or a specific Minister of Education
with a named student. The captions describe the themes honestly rather than claiming
institutional affiliation or endorsement.

## To use your own photos instead

1. Prepare 7 JPEG/PNG images, ideally 1200px wide, landscape 3:2 or 4:3.
2. Replace the files in `static/images/` using the exact filenames in the table above.
3. Edit `HOMEPAGE_PHOTOS` in `server.py` to update `w`, `h`, `alt`, `caption` and `note`.
4. Bump `APP_VERSION` in `server.py` so browsers reload the new images.
5. Commit and push — Render auto-deploys from `main`.

If you have fewer than 7 photos, remove entries from `HOMEPAGE_PHOTOS`; the grid reflows
automatically. See also `static/styles.css` → `.gallery-grid` for layout tweaks.
