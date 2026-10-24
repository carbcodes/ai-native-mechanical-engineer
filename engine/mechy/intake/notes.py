"""Deterministic note skeletons for inspiration/notes/<slug>.md (contracts section 1: <= 300 words).

The skeleton carries the facts a machine can extract (files, keyframe times, transcript
excerpts around mechanism words). A research agent fills in the TODO(research) lines."""

from __future__ import annotations

import re
from typing import Any

from .common import SKELETON_WORD_BUDGET, fmt_ts, keyword_counts, keyword_hits, truncate_words, word_count

TODO = "TODO(research)"
KIND_LABEL = {"youtube": "YouTube video", "video_url": "online video", "video": "video file",
              "image": "image", "image_url": "image", "web": "web page"}


def excerpts(segs: list[tuple[float | None, str]], max_items: int = 6, words: int = 24) -> list[dict]:
    """Transcript/page excerpts around mechanism keywords.
    Consecutive segments with hits form one run; a short run borrows its neighbours for
    context. Runs with more distinct keywords rank first; the result is ordered by position."""
    hits = [i for i, (_, txt) in enumerate(segs) if keyword_hits(txt)]
    runs: list[list[int]] = []
    for i in hits:
        run_words = sum(len(segs[j][1].split()) for j in range(runs[-1][0], runs[-1][1] + 1)) if runs else 0
        if runs and i == runs[-1][1] + 1 and run_words + len(segs[i][1].split()) <= words:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    out = []
    for lo, hi in runs:
        text = " ".join(segs[j][1] for j in range(lo, hi + 1))
        if len(text.split()) < words // 2:
            before = segs[lo - 1][1] if lo > 0 and (lo - 1) not in hits else ""
            after = segs[hi + 1][1] if hi + 1 < len(segs) and (hi + 1) not in hits else ""
            text = " ".join(x for x in (before, text, after) if x)
        tw = text.split()
        first = next((k for k, w in enumerate(tw) if keyword_hits(w)), 0)
        start = max(0, first - words // 3)
        snippet = " ".join(tw[start:start + words])
        snippet = ("... " if start > 0 else "") + snippet + (" ..." if start + words < len(tw) else "")
        out.append({"t": segs[lo][0], "keywords": keyword_hits(text), "text": snippet, "pos": lo})
    ranked = sorted(out, key=lambda e: (-len(e["keywords"]), e["pos"]))[:max_items]
    return sorted(ranked, key=lambda e: e["pos"])


def _what_where(rows: list[tuple[str, str]]) -> list[str]:
    return ["| What | Where |", "|---|---|"] + [f"| {w} | {p} |" for w, p in rows]


def _research_block(kind: str) -> list[str]:
    lines = ["## Research notes", f"- Mechanism and layout: {TODO}",
             f"- Actuators, transmission, bearings, specs (cite timestamps/frames): {TODO}"]
    if kind in ("youtube", "video_url", "video"):
        lines.append(f"- Performance shown (speed, payload, accuracy; measured or claimed): {TODO}")
    caveat = {"web": "page text is extracted automatically and claims on it are unchecked.",
              }.get(kind, "keyframes are picked by scene change, not by meaning, and auto-captions can "
                          "mishear part names.")
    lines += [f"- Copy / avoid for this project: {TODO}", "", f"Not verified: machine-made digest; {caveat}"]
    return lines


def _fit(build, knobs: dict[str, int], order: list[str], budget: int = SKELETON_WORD_BUDGET) -> str:
    """Shrink the optional parts (in `order`) one step at a time until the note fits `budget`."""
    text = build(knobs)
    guard = 0
    while word_count(text) > budget and guard < 200:
        guard += 1
        for k in order:
            if knobs[k] > 0:
                knobs[k] -= 1
                break
        else:
            break
        text = build(knobs)
    return text


def video_note(*, slug: str, kind: str, title: str, source: str, meta: dict[str, Any], frames: list[dict],
               contact: str | None, transcript_rel: str | None, transcript_origin: str | None,
               segs: list[tuple[float, str]], video_rel: str | None, warnings: list[str]) -> str:
    lic = meta.get("license") or "unknown (check before copying)"
    who = meta.get("uploader")
    head = [f"# {title} ({KIND_LABEL.get(kind, kind)})", "",
            "Source: " + " · ".join(x for x in [source, who, fmt_ts(meta.get("duration_s")) if meta.get("duration_s")
                                               else None, f"licence: {lic}"] if x), ""]
    rows = [("Source metadata", f"inspiration/{slug}/source.json")]
    if frames:
        rows.append((f"Keyframes ({len(frames)})", f"inspiration/{slug}/frames/"))
    if contact:
        rows.append(("Contact sheet (all keyframes)", contact))
    if transcript_rel:
        rows.append((f"Transcript ({transcript_origin})", transcript_rel))
    if video_rel:
        rows.append(("Low-res video", video_rel))
    full = " ".join(t for _, t in segs)
    counts = keyword_counts(full)
    ex = excerpts(segs)
    chapters = meta.get("chapters") or []
    desc = re.sub(r"\s+", " ", meta.get("description") or "").strip()

    def build(k: dict[str, int]) -> str:
        L = head + _what_where(rows) + [""]
        if desc and k["desc"]:
            L += [f"Description: {truncate_words(desc, k['desc'])}", ""]
        if frames:
            L += ["## Keyframes", "| # | Time | Frame | Shows |", "|---|---|---|---|"]
            L += [f"| {i} | {fmt_ts(f['t'])} | {f['rel']} | {TODO if i <= k['todo_rows'] else ''} |"
                  for i, f in enumerate(frames, 1)]
            L.append("")
        if chapters and k["chapters"]:
            L += ["Chapters: " + "; ".join(f"{fmt_ts(c['t'])} {c['title']}" for c in chapters[:k["chapters"]]), ""]
        if segs:
            L.append("## Mechanism mentions (transcript)")
            if counts:
                L.append("Counts: " + ", ".join(f"{w} {n}" for w, n in list(counts.items())[:k["counts"]]) + ".")
                for e in ex[:k["excerpts"]]:
                    L.append(f"- {fmt_ts(e['t'])}: \"{truncate_words(e['text'], k['ex_words'])}\"")
            else:
                L.append("No mechanism keywords in the transcript.")
            L.append("")
        elif transcript_origin:
            L += [f"Transcript: none ({transcript_origin}).", ""]
        if warnings and k["warn"]:
            L += ["Intake warnings: " + "; ".join(truncate_words(w, 14) for w in warnings[:k["warn"]]), ""]
        L += _research_block(kind)
        return "\n".join(L) + "\n"

    knobs = {"desc": 30, "chapters": 8, "counts": 8, "excerpts": 6, "ex_words": 24, "warn": 2, "todo_rows": 12}
    return _fit(build, knobs, ["desc", "warn", "excerpts", "chapters", "ex_words", "counts", "todo_rows"])


def web_note(*, slug: str, title: str, source: str, page: dict[str, Any], images: list[dict],
             text_rel: str | None, warnings: list[str]) -> str:
    lic = page.get("license") or "unknown (check before copying)"
    head = [f"# {title} (web page)", "",
            "Source: " + " · ".join(x for x in [source, page.get("site"), page.get("author"), f"licence: {lic}"] if x),
            ""]
    rows = [("Source metadata", f"inspiration/{slug}/source.json")]
    if text_rel:
        rows.append((f"Page text ({page.get('extractor')})", text_rel))
    if images:
        rows.append((f"Images ({len(images)}, EXIF-free)", f"inspiration/{slug}/images/"))
    paras = [p for p in re.split(r"\n\s*\n|\n", page.get("text") or "") if p.strip()]
    segs = [(None, p) for p in paras]
    counts = keyword_counts(page.get("text") or "")
    ex = excerpts(segs)
    desc = re.sub(r"\s+", " ", page.get("description") or "").strip()
    videos = page.get("videos") or []

    def build(k: dict[str, int]) -> str:
        L = head + _what_where(rows) + [""]
        if desc and k["desc"]:
            L += [f"Description: {truncate_words(desc, k['desc'])}", ""]
        if images and k["images"]:
            L += ["## Images", "| # | Image | Alt text | Shows |", "|---|---|---|---|"]
            L += [f"| {i} | {im['rel']} | {truncate_words(im.get('alt') or '', 6)} | {TODO} |"
                  for i, im in enumerate(images[:k["images"]], 1)]
            L.append("")
        L.append("## Mechanism mentions (page text)")
        if counts:
            L.append("Counts: " + ", ".join(f"{w} {n}" for w, n in list(counts.items())[:k["counts"]]) + ".")
            L += [f"- \"{truncate_words(e['text'], k['ex_words'])}\"" for e in ex[:k["excerpts"]]]
        else:
            L.append("No mechanism keywords in the page text.")
        L.append("")
        if videos and k["videos"]:
            L += ["## Embedded videos (digest each with `mechy intake add <url>`)"]
            L += [f"- {v}" for v in videos[:k["videos"]]] + [""]
        if warnings and k["warn"]:
            L += ["Intake warnings: " + "; ".join(truncate_words(w, 14) for w in warnings[:k["warn"]]), ""]
        L += _research_block("web")
        return "\n".join(L) + "\n"

    knobs = {"desc": 40, "images": 6, "counts": 8, "excerpts": 5, "ex_words": 24, "videos": 4, "warn": 2}
    return _fit(build, knobs, ["desc", "warn", "excerpts", "videos", "ex_words", "images", "counts"])


def image_note(*, slug: str, title: str, source: str, image: dict[str, Any], thumb_rel: str | None,
               original_kept: str | None) -> str:
    rows = [("EXIF-free copy", image["rel"])]
    if thumb_rel:
        rows.append(("Thumbnail", thumb_rel))
    rows.append(("Source metadata", f"inspiration/{slug}/source.json"))
    L = [f"# {title} (image)", "",
         f"Source: {source} · {image['width']} x {image['height']} px · original format {image.get('format') or '?'}",
         ""] + _what_where(rows) + [""]
    if original_kept:
        L += [f"The original file stays at {original_kept} (it may still carry EXIF/GPS data).", ""]
    L += ["## Research notes", f"- What it shows: {TODO}", f"- Mechanism and layout: {TODO}",
          f"- Parts, sizes and specs visible (estimate scale from known parts): {TODO}",
          f"- Copy / avoid for this project: {TODO}", "",
          "Not verified: machine-made digest; nothing in the picture has been measured."]
    return "\n".join(L) + "\n"
