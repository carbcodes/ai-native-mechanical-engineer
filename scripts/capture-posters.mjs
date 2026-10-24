import { chromium } from "@playwright/test";
import sharp from "sharp";

// Run against `npm run dev -- --port 5173`. Both assets are original renders
// of the procedural workshop, with no reference-site imagery.
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 900 },
    reducedMotion: "reduce",
  });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.locator(".makerspace-scene.is-ready").waitFor();
  await page.waitForTimeout(700);
  await sharp(await page.screenshot())
    .resize(1200, 630, { fit: "cover", position: "top" })
    .jpeg({ quality: 85 })
    .toFile("public/social-preview.jpg");
  await page.addStyleTag({
    content:
      ".site-header,.journey-copy,.journey-veil,.journey-bottom,.journey-topline,.journey-progress { visibility:hidden!important; }",
  });
  await sharp(await page.screenshot())
    .webp({ quality: 85 })
    .toFile("public/makerspace-poster.webp");
  console.log("Created the makerspace fallback and social preview.");
} finally {
  await browser.close();
}
