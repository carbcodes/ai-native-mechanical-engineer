"""Inspiration intake (mechy.intake). Offline: a tiny ffmpeg testsrc video, generated images and a
local HTML page served from 127.0.0.1. The live YouTube test runs only with MECHY_NET_TESTS=1."""

import argparse
import asyncio
import functools
import http.server
import importlib.util
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
import yaml

from mechy.events import Events
from mechy.intake import IntakeError, classify, digest, digest_all, pending
from mechy.intake import notes as N
from mechy.intake import video as V
from mechy.intake.common import NOTE_WORD_LIMIT, SKELETON_WORD_BUDGET, word_count, youtube_id
from mechy.project import init_project

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")

HAS_YTDLP = importlib.util.find_spec("yt_dlp") is not None

VTT = """WEBVTT

00:00:00.500 --> 00:00:03.000
Here is the base with a NEMA 17 stepper and a GT2 belt.

00:00:03.000 --> 00:00:06.000
The elbow uses a 608 bearing on an 8 mm shaft.

00:00:06.000 --> 00:00:09.000
Then we paint it red.

00:00:09.000 --> 00:00:11.500
A small servo opens the gripper to catch the ball.
"""

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Belt-driven arm build log</title>
<meta name="description" content="A three-axis arm with motors in the base and GT2 belts to every joint.">
<link rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">
</head><body>
<nav>Home | Projects | About</nav>
<article>
<h1>Belt-driven arm build log</h1>
<p>All three NEMA 17 stepper motors sit in the base, so the arm itself stays light.</p>
<p>Each joint is driven by a closed GT2 belt over a 20 tooth pulley and a printed 60 tooth pulley,
a 3:1 reduction. The shoulder runs on two 608-2RS bearings.</p>
<p>The wrist servo was dropped because it added 40 g at the end of the arm and cost torque at the shoulder.</p>
<img src="img/arm.jpg" alt="Arm on the bench" width="640" height="480">
<img src="img/logo.png" alt="site logo">
<img src="img/tiny.jpg" width="32" height="32">
<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>
</article>
<footer>Copyright footer text that should not be in the main text</footer>
</body></html>
"""


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, timeout=120)


@pytest.fixture(scope="module")
def assets(tmp_path_factory):
    """clip.mp4 (8 s test pattern + 4 s red, with a sine tone) + clip.vtt, page.html, images."""
    d = tmp_path_factory.mktemp("assets")
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=8:size=320x240:rate=10",
            "-f", "lavfi", "-i", "color=c=red:duration=4:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
            "-filter_complex", "[0][1]concat=n=2:v=1[v]", "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(d / "clip.mp4"))
    (d / "clip.vtt").write_text(VTT)
    from PIL import Image
    (d / "img").mkdir()
    im = Image.new("RGB", (800, 600), (40, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"            # Make
    exif[0x0112] = 6                      # Orientation: rotate 90 CW on display
    exif[0x8825] = {1: "N", 2: (37.0, 46.0, 30.0)}   # GPS IFD
    im.save(d / "photo.jpg", exif=exif)
    Image.new("RGB", (640, 480), (200, 80, 40)).save(d / "img" / "arm.jpg")
    Image.new("RGB", (300, 300), (0, 0, 0)).save(d / "img" / "logo.png")
    Image.new("RGB", (32, 32), (0, 0, 0)).save(d / "img" / "tiny.jpg")
    (d / "page.html").write_text(PAGE)
    return d


@pytest.fixture(scope="module")
def server(assets):
    """Serve the assets folder on 127.0.0.1 (no proxy) for the URL code paths."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(assets))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def proj(tmp_path):
    return init_project(tmp_path / "proj", git=False)


def _note(proj, res):
    return proj.path(res["note"]).read_text()


# ------------------------------------------------------------------- units
def test_classify(tmp_path, assets):
    assert classify("https://youtu.be/dQw4w9WgXcQ").kind == "youtube"
    assert classify("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30").kind == "youtube"
    assert youtube_id("https://www.youtube.com/shorts/abcdefghijk") == "abcdefghijk"
    assert classify("https://vimeo.com/12345").kind == "video_url"
    assert classify("https://example.com/a/clip.mp4?x=1").kind == "video_url"
    assert classify("https://example.com/pic.PNG").kind == "image_url"
    assert classify("https://www.printables.com/model/1-arm").kind == "web"
    assert classify(assets / "clip.mp4").kind == "video"
    assert classify(assets / "photo.jpg").kind == "image"
    assert classify(assets / "page.html").kind == "web"
    assert classify((assets / "page.html").as_uri()).kind == "web"
    with pytest.raises(IntakeError):
        classify(tmp_path / "missing.mp4")
    (tmp_path / "x.txt").write_text("hi")
    with pytest.raises(IntakeError):
        classify(tmp_path / "x.txt")


def test_youtube_rollup_captions_are_deduplicated():
    vtt = """WEBVTT
Kind: captions

00:00:01.000 --> 00:00:03.000 align:start position:0%
the<00:00:01.500><c> stepper</c><00:00:02.000><c> drives</c>

00:00:03.000 --> 00:00:03.010
the stepper drives

00:00:03.010 --> 00:00:05.000
the stepper drives
a GT2 belt &amp; pulley
"""
    segs = V.parse_subtitles(vtt)
    assert segs == [(1.0, "the stepper drives"), (3.01, "a GT2 belt & pulley")]


def test_pick_times_limits_and_determinism():
    scores = [(t / 4, 0.9 if t % 40 == 0 else 0.01) for t in range(1, 4 * 600)]
    a = V.pick_times(600, scores, 12)
    assert a == V.pick_times(600, scores, 12)
    assert len(a) == 12 and [t for t, _ in a] == sorted(t for t, _ in a)
    assert all(0 <= t < 600 for t, _ in a)
    assert sum(1 for _, s in a if s is not None) >= 6          # scene cuts first
    assert len(V.pick_times(3.0, [], 12)) == 1
    assert len(V.pick_times(6.0, [], 12)) == 3


def test_long_video_note_stays_under_budget():
    segs = [(i * 4.0, f"the stepper turns a gear and the belt drives a pulley with bearing number {i} "
                      f"and some servo torque words to pad the line out further") for i in range(400)]
    frames = [{"t": i * 50.0, "rel": f"inspiration/yt-abc/frames/{i + 1:02d}_{i:02d}m00s.jpg"} for i in range(12)]
    meta = {"uploader": "Someone", "duration_s": 600, "license": "Creative Commons Attribution license (reuse allowed)",
            "description": "word " * 300, "chapters": [{"t": i * 60, "title": f"Chapter {i} gearbox"} for i in range(10)]}
    note = N.video_note(slug="yt-abc", kind="youtube", title="A long robot arm build video with a long title",
                        source="https://www.youtube.com/watch?v=abcdefghijk", meta=meta, frames=frames,
                        contact="inspiration/yt-abc/contact.jpg", transcript_rel="inspiration/yt-abc/transcript.txt",
                        transcript_origin="auto-captions, en", segs=segs, video_rel="inspiration/yt-abc/video.mp4",
                        warnings=["a warning " * 20])
    assert word_count(note) <= SKELETON_WORD_BUDGET
    assert "TODO(research)" in note and "## Keyframes" in note and "| What | Where |" in note


# ----------------------------------------------------------- local video
def test_digest_local_video(proj, assets, tmp_path):
    src = tmp_path / "arm_demo.mp4"
    shutil.copy(assets / "clip.mp4", src)
    shutil.copy(assets / "clip.vtt", tmp_path / "arm_demo.vtt")
    ev = Events(proj.root, quiet=True)
    r = digest(proj, src, events=ev)
    assert r["ok"] and r["kind"] == "video" and r["slug"] == "arm-demo"
    assert 3 <= len(r["frames"]) <= 12
    assert all(proj.path(f).stat().st_size > 200 for f in r["frames"])
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["duration_s"] == pytest.approx(12, abs=0.3)
    assert sj["has_audio"] is True and sj["width"] == 320
    assert any(f["scene_score"] for f in sj["frames"])            # the cut to red at 8 s is found
    cut = next(f for f in sj["frames"] if f["scene_score"])
    assert 8.0 <= cut["t"] <= 8.6
    assert sj["transcript"]["origin"] == "sidecar arm_demo.vtt"
    assert "license" in sj and sj["note"] == "inspiration/notes/arm-demo.md"
    assert proj.path("inspiration/arm-demo/contact.jpg").exists()
    t = proj.path(r["transcript"]).read_text()
    assert t.splitlines()[0] == "[0:00] Here is the base with a NEMA 17 stepper and a GT2 belt."
    note = _note(proj, r)
    assert word_count(note) <= SKELETON_WORD_BUDGET <= NOTE_WORD_LIMIT
    assert note.splitlines()[0] == "# arm demo (video file)"
    assert "| What | Where |" in note and "TODO(research)" in note
    assert "stepper" in note and "servo opens the gripper to catch" in note
    for f in r["frames"]:
        assert f in note                                             # keyframe table has every frame path
    # file.written events for the frames and the note
    log = [json.loads(l) for l in proj.path(".mechy/events.jsonl").read_text().splitlines()]
    written = {e["path"] for e in log if e["type"] == "file.written"}
    assert r["note"] in written and r["frames"][0] in written
    # deterministic: a second run gives the same note and frame list
    r2 = digest(proj, src)
    assert r2["slug"] == r["slug"] and r2["frames"] == r["frames"] and _note(proj, r2) == note


def test_video_without_subtitles_and_without_whisper(proj, assets, monkeypatch):
    dst = proj.path("inspiration", "drop.mp4")
    shutil.copy(assets / "clip.mp4", dst)
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", None)   # force "not installed"
    r = digest(proj, "inspiration/drop.mp4")
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert r["transcript"] is None and "faster-whisper" in sj["transcript"]["origin"]
    assert sj["path"] == "inspiration/drop.mp4"
    assert "Transcript: none" in _note(proj, r)
    r = digest(proj, "inspiration/drop.mp4", transcribe=False)
    assert "transcription off" in json.loads(proj.path(r["source_json"]).read_text())["transcript"]["origin"]


def test_edited_note_is_not_overwritten(proj, assets):
    r = digest(proj, assets / "clip.mp4")
    p = proj.path(r["note"])
    p.write_text(p.read_text().replace("Mechanism and layout: TODO(research)", "Mechanism and layout: belt arm"))
    r2 = digest(proj, assets / "clip.mp4")
    assert "belt arm" in p.read_text()
    assert proj.path("inspiration/clip/note.skeleton.md").exists()
    assert any("was edited" in w for w in r2["warnings"])
    digest(proj, assets / "clip.mp4", force=True)
    assert "belt arm" not in p.read_text() and not proj.path("inspiration/clip/note.skeleton.md").exists()


# ------------------------------------------------------------------ images
def test_digest_image_strips_exif(proj, assets):
    from PIL import Image
    with Image.open(assets / "photo.jpg") as im:
        assert im.getexif().get(0x010F) == "SecretCam"
    r = digest(proj, assets / "photo.jpg")
    assert r["kind"] == "image" and r["images"] == ["inspiration/photo/image.jpg"]
    out = proj.path("inspiration/photo/image.jpg")
    raw = out.read_bytes()
    assert b"SecretCam" not in raw and b"Exif" not in raw
    with Image.open(out) as im:
        assert not im.getexif() and im.size == (600, 800)          # orientation applied, then dropped
    assert proj.path("inspiration/photo/thumb.jpg").exists()
    assert not any(p.name == "photo.jpg" for p in proj.path("inspiration").rglob("*"))   # original not copied in
    note = _note(proj, r)
    assert "600 x 800 px" in note and "What it shows: TODO(research)" in note
    assert word_count(note) <= SKELETON_WORD_BUDGET


# --------------------------------------------------------------------- web
def test_digest_local_html(proj, assets):
    r = digest(proj, assets / "page.html")
    assert r["kind"] == "web" and r["title"] == "Belt-driven arm build log"
    assert r["images"] == ["inspiration/page/images/01.jpg"]                 # logo and 32 px icon skipped
    assert r["embedded_videos"] == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    text = proj.path("inspiration/page/page.txt").read_text()
    assert "608-2RS" in text and "Copyright footer" not in text
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["license"].startswith("CC BY-SA 4.0")
    note = _note(proj, r)
    assert "licence: CC BY-SA 4.0" in note and "stepper" in note.lower()
    assert "mechy intake add" in note and word_count(note) <= SKELETON_WORD_BUDGET
    # local files are not links: links.yaml is untouched
    assert yaml.safe_load(proj.path("inspiration/links.yaml").read_text()) == {"links": []}


def test_digest_web_url_updates_links_yaml(proj, server):
    url = f"{server}/page.html"
    proj.path("inspiration/links.yaml").write_text(
        yaml.safe_dump({"links": [{"url": url, "added": "2026-10-01T00:00:00+00:00"},
                                  {"url": "https://example.com/other", "added": "2026-10-02T00:00:00+00:00"}]}))
    assert pending(proj) == [url, "https://example.com/other"]
    r = digest(proj, url)
    assert r["slug"].startswith("127-0-0-") and len(r["images"]) == 1
    links = yaml.safe_load(proj.path("inspiration/links.yaml").read_text())["links"]
    assert links[0] == {"url": url, "added": "2026-10-01T00:00:00+00:00", "title": "Belt-driven arm build log",
                        "digested": r["note"]}
    assert "digested" not in links[1]
    assert pending(proj) == ["https://example.com/other"]


def test_digest_image_url_adds_link(proj, server):
    r = digest(proj, f"{server}/img/arm.jpg")
    assert r["kind"] == "image_url"
    links = yaml.safe_load(proj.path("inspiration/links.yaml").read_text())["links"]
    assert links[0]["url"].endswith("/img/arm.jpg") and links[0]["digested"] == r["note"] and "added" in links[0]


@pytest.mark.skipif(not HAS_YTDLP, reason="yt-dlp not installed")
def test_digest_video_url_through_ytdlp(proj, server):
    r = digest(proj, f"{server}/clip.mp4")
    assert r["kind"] == "video_url" and len(r["frames"]) >= 3
    assert proj.path(f"inspiration/{r['slug']}/.gitignore").read_text().strip().endswith("video.*")
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["video"].startswith(f"inspiration/{r['slug']}/video.") and sj["duration_s"] == pytest.approx(12, abs=0.5)
    assert word_count(_note(proj, r)) <= SKELETON_WORD_BUDGET


def test_pending_and_digest_all(proj, assets):
    shutil.copy(assets / "photo.jpg", proj.path("inspiration", "bench.jpg"))
    proj.path("inspiration/links.yaml").write_text(yaml.safe_dump({"links": [{"url": (assets / "page.html").as_uri(),
                                                                              "added": "x"}]}))
    assert pending(proj) == [(assets / "page.html").as_uri(), "inspiration/bench.jpg"]
    res = digest_all(proj)
    assert res["ok"] and len(res["digested"]) == 2 and pending(proj) == []
    assert proj.path("inspiration/notes/bench.md").exists()


# ----------------------------------------------------- CLI and MCP snippets
def test_register_cli_snippet(proj, assets):
    from mechy.cli import _common
    from mechy.intake.register import add_intake_parser, run_intake_cli
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    add_intake_parser(sub, _common)
    args = ap.parse_args(["intake", "add", str(assets / "photo.jpg"), str(assets / "nope.mp4"), "--json"])
    ev = Events(proj.root, quiet=True)
    res = run_intake_cli(proj, args, ev)
    assert res["ok"] is False and len(res["digested"]) == 1 and "nope.mp4" in res["errors"][0]["error"]
    res = run_intake_cli(proj, ap.parse_args(["intake", "pending"]), ev)
    assert res == {"ok": True, "pending": [], "count": 0}


def test_register_mcp_snippet(proj, assets):
    from mcp.server.fastmcp import FastMCP
    from mechy.intake.register import register_mcp_tools
    s = FastMCP("t")
    register_mcp_tools(s, proj)
    assert {t.name for t in asyncio.run(s.list_tools())} == {"intake_digest", "intake_pending"}
    res = asyncio.run(s.call_tool("intake_digest", {"source": str(assets / "page.html")}))
    content = res[0] if isinstance(res, tuple) else res
    out = json.loads(content[0].text)
    assert out["ok"] and out["note"] == "inspiration/notes/page.md"
    bad = asyncio.run(s.call_tool("intake_digest", {"source": "/nope/x.mp4"}))
    content = bad[0] if isinstance(bad, tuple) else bad
    assert json.loads(content[0].text)["ok"] is False


def test_prompts_use_digests():
    from mechy.agents.providers import role_prompt
    assert "inspiration/notes/" in role_prompt("research") and "TODO(research)" in role_prompt("research")
    assert "intake" in role_prompt("planner") and "inspiration/notes/" in role_prompt("planner")


# -------------------------------------------------------------------- live
@pytest.mark.skipif(os.environ.get("MECHY_NET_TESTS") != "1", reason="set MECHY_NET_TESTS=1 for live network tests")
def test_live_youtube(proj):
    url = os.environ.get("MECHY_TEST_YOUTUBE", "https://www.youtube.com/watch?v=jNQXAC9IVRw")   # "Me at the zoo", 19 s
    r = digest(proj, url)
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["title"] and sj["duration_s"] and r["frames"]
    assert word_count(_note(proj, r)) <= NOTE_WORD_LIMIT


def test_html_fallback_without_trafilatura(monkeypatch):
    from mechy.intake.web import parse_page
    monkeypatch.setitem(__import__("sys").modules, "trafilatura", None)
    p = parse_page(PAGE, "file:///x/page.html")
    assert p["extractor"] in ("html.parser", "readability-lxml")
    assert "608-2RS" in p["text"] and "Copyright footer" not in p["text"] and "Projects" not in p["text"]


# ------------------------------------------------------------- pdf/text/cad
def test_digest_pdf(proj, tmp_path):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.add_metadata({"/Title": "Gearbox notes"})
    src = tmp_path / "doc.pdf"
    with open(src, "wb") as f:
        w.write(f)
    r = digest(proj, str(src))
    assert r["kind"] == "pdf"
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["kind"] == "pdf" and sj["pages"] == 1 and sj["title"] == "Gearbox notes"
    assert proj.path(f"inspiration/{r['slug']}/doc.pdf").exists()
    assert proj.path(f"inspiration/{r['slug']}/text.txt").exists()


def test_digest_text_and_markdown(proj, tmp_path):
    src = tmp_path / "idea.md"
    src.write_text("# Drawbot\n\nA belt-driven XY plotter with NEMA steppers and GT2 belts.\n")
    r = digest(proj, str(src))
    assert r["kind"] == "text" and r["slug"] == "idea"
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["kind"] == "text" and sj["file"] == f"inspiration/{r['slug']}/idea.md"
    note = _note(proj, r)
    assert "belt" in note.lower() and "TODO(research)" in note


STL = """solid tri
facet normal 0 0 1
 outer loop
  vertex 0 0 0
  vertex 10 0 0
  vertex 0 10 0
 endloop
endfacet
facet normal 0 0 -1
 outer loop
  vertex 0 0 5
  vertex 0 10 0
  vertex 10 0 0
 endloop
endfacet
endsolid tri
"""


def test_digest_cad_stl(proj, tmp_path):
    src = tmp_path / "mount.stl"
    src.write_text(STL)
    r = digest(proj, str(src))
    assert r["kind"] == "cad"
    sj = json.loads(proj.path(r["source_json"]).read_text())
    assert sj["kind"] == "cad" and sj["file_type"] == "stl"
    if "bbox_mm" in sj:      # bbox when build123d can import the STL
        assert sj["bbox_mm"] == [10, 10, 5]


def test_pending_counts_new_kinds(proj, tmp_path):
    (proj.path("inspiration") / "doc.pdf").write_bytes(b"%PDF-1.4\n")
    (proj.path("inspiration") / "notes.md").write_text("hi\n")
    assert set(pending(proj)) == {"inspiration/doc.pdf", "inspiration/notes.md"}
