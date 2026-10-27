# Homepage photo gallery — sources and how to replace images

The homepage gallery shows **7 real photographs** (not AI-generated). They are stock photos
from [Pexels](https://www.pexels.com/license/) and are free to use for commercial and
non-commercial purposes, with no attribution required (attribution is still given below).

## Files in `static/images/`

| # | File | Caption shown | Pexels photo | Photographer / source |
| --- | --- | --- | --- | --- |
| 1 | `students-classroom.jpg` | Students in class | [7092450](https://www.pexels.com/photo/7092450/) | Pexels stock |
| 2 | `isomo-academy.jpg` | Isomo Academy scholars | [8618024](https://www.pexels.com/photo/8618024/) | Pexels stock |
| 3 | `yale-scholars.jpg` | Yale scholars | [7972324](https://www.pexels.com/photo/7972324/) | Pexels stock |
| 4 | `escm-students.jpg` | ESCM students | [6549913](https://www.pexels.com/photo/6549913/) | Pexels stock |
| 5 | `education-leader.jpg` | Education leadership & students | [8419491](https://www.pexels.com/photo/8419491/) | Pexels stock |
| 6 | `focused-scholar.jpg` | Focused scholars | [6281959](https://www.pexels.com/photo/6281959/) | Pexels stock |
| 7 | `graduation.jpg` | Graduation day | [35487002](https://www.pexels.com/photo/35487002/) | Pexels stock |

All files are 1200px wide JPEGs, optimised (~100–200 KB each), so the page stays fast on
mobile connections.

> ⚠️ **Important — these are stock photos, not photos of the named institutions or people.**
> The captions describe the *theme* of each slot. They are **not** genuine photographs of
> Isomo Academy scholars, Yale scholars, ESCM students, or Rwanda's Minister of Education
> with a student. Do not present them as documentary evidence of a partnership or
> endorsement. Replace them with your own authorised photos before making such claims.

## To use your own real photos

1. Prepare 7 JPEG/PNG images (1200px wide or larger, landscape 3:2 or 4:3 works best).
2. Replace the files in `static/images/` using the **exact same filenames** listed above.
3. Edit `HOMEPAGE_PHOTOS` in `server.py` to update `alt` text, `caption`, and `note` so they
   accurately describe the real people in each photo.
4. Bump `APP_VERSION` in `server.py` (e.g. `v14-...` → `v15-...`) so browsers reload the new
   images instead of serving cached ones.
5. Commit and push — Render auto-deploys from `main`.

If you have fewer than 7 photos, remove the corresponding entries from `HOMEPAGE_PHOTOS`;
the grid reflows automatically.

## Licence note

Pexels photos are free under the [Pexels License](https://www.pexels.com/license/): you may
use them commercially, modify them, and you do not have to credit the photographer. However,
identifiable people in stock photos must not be used in a way that implies they endorse a
product, cause, or organisation — which is another reason to swap in your own community
photos if these are meant to represent real 70Scholar students.
