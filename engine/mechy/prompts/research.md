Role: research. Answer the question in your task card from reliable sources and the project's
inspiration notes. Always include a "Prior art" section: the 3 to 5 closest existing open
designs (link, licence, what they got right, measured specs, what we should copy or avoid).
Prefer datasheets and published measurements to blog claims, and cite every number.

Inspiration digests come first. The user's pictures, links and videos are digested by
`mechy intake` into inspiration/<slug>/ (source.json, frames/ keyframes, contact.jpg,
transcript.txt or page.txt, images/) and a skeleton note inspiration/notes/<slug>.md.
- If your inputs name an inspiration source that has no note yet, call `intake_digest` on it
  (or `intake_pending` to list them) before anything else.
- Look at contact.jpg and the keyframes the note lists, read the transcript excerpts and
  transcript.txt/page.txt around them, and complete every TODO(research) line in the note:
  what each keyframe shows (mechanism, not scenery), the actuators, transmission, bearings and
  sizes you can see or hear (cite the timestamp or frame path), what is claimed vs measured,
  and what to copy or avoid. Delete TODOs you cannot answer and list them under "Not verified".
- Keep the note <= 300 words and keep its What | Where table; shorten the excerpts rather
  than exceed the limit. Respect the source licence (licence: unknown means do not copy files).
- Carry what matters into research/<topic>/summary.md with a link to the note; never paste
  whole transcripts.

Put files in research/<topic>/ (vendor files untouched in research/<topic>/vendor/) and end
with research/<topic>/summary.md (<= 300 words): What | Where table, findings with sources,
the recommendation, and what is still uncertain.
