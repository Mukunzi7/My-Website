# Slideshow image provenance and permission checklist

The old seven-photo static homepage gallery was removed; the slideshow remains. The website
itself does not display source or credit lines below the images. Keep this file as an
operational provenance record (the repository may itself be public).

## Owner-supplied homepage hero photo

`static/images/hero-school-group.jpg` was provided directly by the site owner for the
homepage hero. The image file has been re-encoded without source metadata and is not
cropped, but browsers crop it responsively to fill the opening section. Its presence in the repository does not establish publication rights or consent. The owner
should obtain appropriate permission and any required consent for identifiable people,
especially children, before public use.

## Owner-managed slideshow

Admin → Slideshow photos supports JPEG, PNG and WebP up to 8 MB, at most 36 megapixels.
Photos are normalized to JPEG, resized to fit within 1920 pixels per side and stripped of
metadata. New photos appear first; an optional description is displayed and used as alt
text. The owner may remove bundled or uploaded images. Removing a bundled image hides its
direct website URL but does not erase the copy in the public source repository, caches,
backups or elsewhere. SQLite stores uploaded image data and the selection, so include the
database in backups. Without persistent storage, deploys or restarts can erase changes.
Do not publish an image without the required permissions.

## New slideshow photos

All of the following were downloaded from Pexels and are photographs, not generated images.
Pexels says they are free for website use and do not require attribution; its terms prohibit
implying endorsement and other uses. Confirm the current licence and any needed consent
before use, especially for identifiable minors.

| Local file | Pexels source | Listed photographer / subject |
| --- | --- | --- |
| `ilead-students.jpg` | <https://www.pexels.com/photo/29942773/> | iLead Rwanda, students outside a school |
| `ilead-classmates.jpg` | <https://www.pexels.com/photo/two-students-posing-in-school-uniform-outdoors-30649794/> | iLead Rwanda, classmates |
| `students-reading.jpg` | <https://www.pexels.com/photo/group-of-students-reading-a-book-10638213/> | Ron Lach, students reading; **not verified as an iLead book** |
| `university-graduation.jpg` | <https://www.pexels.com/photo/standing-students-in-academic-dress-15490406/> | Safari Consoler, university graduates |
| `graduation-speech.jpg` | <https://www.pexels.com/photo/woman-in-a-graduation-gown-giving-a-speech-and-smiling-12496871/> | Amos Getanda, a graduate speaking |

Pexels licence: <https://www.pexels.com/license/>. iLead Rwanda's Pexels profile:
<https://www.pexels.com/@ilead-rwanda-2148150079/>. The captions do not claim that the
people or organizations endorse 70Scholar. The iLead Rwanda source is identified by its
Pexels profile; the displayed photos are not verified to have come from an iLead book.
A picture of an actual iLead curriculum booklet is visible at
<https://leadershiptb.org/ilead/>, but no reuse licence for that image was established, so
it was not copied. Obtain permission or an owner-supplied image before adding it.

## Earlier slideshow photos retained at the user's request

`slide-01.jpg` through `slide-12.jpg` were obtained previously from the website of Rwanda's
National Examination and School Inspection Authority (NESA), <https://www.nesa.gov.rw/>.
No express open licence for those pictures was established. Some include identifiable
students. Before continuing to use them on a public site, obtain permission and any required
consent, or replace them with properly licensed/owner-supplied photos. Removing source wording
from the site does not itself grant permission. Consult the repository history for the
original source-path details.
