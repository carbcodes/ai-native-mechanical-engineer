import { expect, test } from "@playwright/test";

test("loads the workbench without runtime errors or clipped branding", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.locator(".makerspace-scene.is-ready")).toBeVisible();
  await expect(page.getByRole("heading", { name: "mechy." })).toBeVisible();
  const brand = await page.locator(".journey-hero h1").evaluate((el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    return { right: range.getBoundingClientRect().right, width: innerWidth };
  });
  expect(brand.right).toBeLessThanOrEqual(brand.width);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("explains recurring billing and hands off to the real VibeWrite flow", async ({
  page,
}) => {
  await page.goto("/");
  const trigger = page.getByRole("button", {
    name: "Get the demo",
    exact: true,
  });
  await trigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("$19.99");
  await expect(dialog).toContainText("Recurring VibeWrite Pro subscription");
  await expect(dialog).toContainText(
    "Mechy access and demo scheduling are arranged separately",
  );
  await expect(
    dialog.getByRole("link", { name: "Continue to VibeWrite" }),
  ).toHaveAttribute("href", /^https:\/\/www\.vibewrite\.work\/pricing\?/);
  await expect(
    dialog.getByRole("link", { name: /Email us/ }),
  ).toHaveAttribute("href", /^mailto:hello@example\.com\?/);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("native scrolling travels through one persistent 3D room", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  const canvas = page.locator(".makerspace-scene canvas");
  await expect(canvas).toHaveAttribute("data-camera-position", /,/);
  const start = await canvas.getAttribute("data-camera-position");
  await canvas.evaluate((el) =>
    el.setAttribute("data-persistent-room", "original"),
  );
  if (testInfo.project.name === "mobile") {
    // A real touch drag over the WebGL area must scroll the document.
    const client = await page.context().newCDPSession(page);
    await client.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [{ x: 190, y: 620 }],
    });
    for (let y = 600; y >= 230; y -= 30) {
      await client.send("Input.dispatchTouchEvent", {
        type: "touchMove",
        touchPoints: [{ x: 190, y }],
      });
      await page.waitForTimeout(20);
    }
    await client.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await client.detach();
  } else {
    await page.mouse.move(1000, 500);
    await page.mouse.wheel(0, 800);
  }
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(100);
  await expect
    .poll(() => canvas.getAttribute("data-camera-position"))
    .not.toBe(start);
  await page
    .locator(".journey-nav")
    .getByRole("button", { name: "Source", exact: true })
    .click();
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Find the lowest-cost parts that fit your design.",
  );
  await expect
    .poll(async () =>
      Number(
        (await canvas.getAttribute("data-camera-position"))?.split(",")[2],
      ),
    )
    .toBeLessThan(-8);
  await page
    .locator(".journey-nav")
    .getByRole("button", { name: /Build/ })
    .click();
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Bring it all together in a working prototype.",
  );
  await expect
    .poll(async () =>
      Number(
        (await canvas.getAttribute("data-camera-position"))?.split(",")[2],
      ),
    )
    .toBeLessThan(-16);
  await expect(canvas).toHaveAttribute("data-persistent-room", "original");
  await expect(page.locator("canvas")).toHaveCount(1);
  await page
    .locator(".journey-nav")
    .getByRole("button", { name: /Welcome/ })
    .click();
  await expect
    .poll(async () =>
      Number(
        (await canvas.getAttribute("data-camera-position"))?.split(",")[2],
      ),
    )
    .toBeGreaterThan(10);
});

test("stations and motion can be controlled explicitly", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".makerspace-scene.is-ready")).toBeVisible();
  const nav = page.locator(".journey-nav");
  await nav.getByRole("button", { name: /Design/ }).click();
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Shape every detail with CAD and CAM.",
  );
  await nav.getByRole("button", { name: /Understand/ }).click();
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Work out the physics before you build.",
  );
  await page.getByRole("button", { name: "Pause journey motion" }).click();
  const paused = page.getByRole("button", { name: "Resume journey motion" });
  await expect(paused).toHaveAttribute("aria-pressed", "true");
  const canvas = page.locator(".makerspace-scene canvas");
  const position = await canvas.getAttribute("data-camera-position");
  const caption = await page.locator(".journey-chapter h2").innerText();
  await page.evaluate(() => {
    const journey = document.querySelector<HTMLElement>(".journey")!;
    window.scrollTo({
      top: (journey.offsetHeight - innerHeight) * 0.6,
      behavior: "instant",
    });
  });
  await page.waitForTimeout(300);
  await expect(canvas).toHaveAttribute("data-camera-position", position!);
  await expect(page.locator(".journey-chapter h2")).toHaveText(caption);
  await paused.click();
  await expect(
    page.getByRole("button", { name: "Pause journey motion" }),
  ).toHaveAttribute("aria-pressed", "false");
});

test("the fabrication caption follows the camera around the whiteboard", async ({
  page,
}) => {
  await page.goto("/");
  const canvas = page.locator(".makerspace-scene canvas");
  await expect(canvas).toHaveAttribute("data-camera-progress", /[0-9]/);
  const seek = async (progress: number) => {
    await page.evaluate((progress) => {
      const journey = document.querySelector<HTMLElement>(".journey")!;
      window.scrollTo({
        top: (journey.offsetHeight - innerHeight) * progress,
        behavior: "instant",
      });
    }, progress);
    await expect
      .poll(async () =>
        Math.abs(
          Number(await canvas.getAttribute("data-camera-progress")) - progress,
        ),
      )
      .toBeLessThan(0.001);
  };
  await seek(0.4);
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Work out the physics before you build.",
  );
  // Clear the caption while passing the edge, in either scroll direction.
  await seek(0.5);
  await expect(page.locator(".journey-copy")).toHaveCSS("opacity", "0");
  const samples = await page.evaluate(async () => {
    const journey = document.querySelector<HTMLElement>(".journey")!;
    window.scrollTo({
      top: (journey.offsetHeight - innerHeight) * 0.6,
      behavior: "instant",
    });
    const seen: number[][] = [];
    const started = performance.now();
    while (performance.now() - started < 1300) {
      await new Promise(requestAnimationFrame);
      const copy = document.querySelector<HTMLElement>(".journey-copy")!;
      if (
        copy.innerText.includes("CAD and CAM") &&
        Number(getComputedStyle(copy).opacity) > 0.1
      ) {
        seen.push(
          document
            .querySelector("canvas")!
            .dataset.cameraPosition!.split(",")
            .map(Number),
        );
      }
    }
    return seen;
  });
  expect(samples.length).toBeGreaterThan(0);
  // The board is at z=-3.2: visible fabrication copy must follow clearance.
  expect(samples.every((position) => position[2] < -4)).toBe(true);
  const position = (await canvas.getAttribute("data-camera-position"))!
    .split(",")
    .map(Number);
  expect(position[0]).toBeGreaterThan(3);
  expect(Math.hypot(position[0] - 5.7, position[2] + 11.4)).toBeLessThan(7.5);
  await seek(0.5);
  await expect(page.locator(".journey-copy")).toHaveCSS("opacity", "0");
  await seek(0.4);
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Work out the physics before you build.",
  );
});

test("the final robot gently follows the mouse and freezes when paused", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name === "mobile",
    "Mouse interaction requires a hover device",
  );
  await page.goto("/");
  const canvas = page.locator(".makerspace-scene canvas");
  await expect(canvas).toHaveAttribute("data-robot-pose", /,/);
  await page
    .locator(".journey-nav")
    .getByRole("button", { name: "Build", exact: true })
    .click();
  await expect(canvas).toHaveAttribute("data-camera-progress", "1.0000");
  const camera = await canvas.getAttribute("data-camera-position");
  const pose = async () =>
    (await canvas.getAttribute("data-robot-pose"))!.split(",").map(Number);
  await page.mouse.move(250, 450);
  await expect.poll(async () => (await pose())[0]).toBeLessThan(-0.055);
  const left = await pose();
  await page.mouse.move(1300, 450);
  await expect.poll(async () => (await pose())[0]).toBeGreaterThan(0.075);
  const right = await pose();
  expect(right[1]).toBeLessThan(left[1]);
  expect(right[2]).toBeGreaterThan(left[2]);
  // A restrained response: no tracked joint swings by more than 25 degrees.
  expect(right.every((angle, i) => Math.abs(angle - left[i]) < 0.44)).toBe(true);
  await expect(canvas).toHaveAttribute("data-camera-position", camera!);
  await page.getByRole("button", { name: "Pause journey motion" }).click();
  const frozen = await canvas.getAttribute("data-robot-pose");
  await page.mouse.move(300, 200);
  await page.waitForTimeout(300);
  await expect(canvas).toHaveAttribute("data-robot-pose", frozen!);
  await page.getByRole("button", { name: "Resume journey motion" }).click();
  await page.mouse.move(300, 200);
  await expect.poll(() => canvas.getAttribute("data-robot-pose")).not.toBe(frozen);
});

test("FAQ and mobile navigation are usable", async ({ page }, testInfo) => {
  await page.goto("/");
  if (testInfo.project.name === "mobile") {
    await page.getByRole("button", { name: "Open navigation" }).click();
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "Your next build" })
      .click();
    await expect(
      page.getByRole("button", { name: "Open navigation" }),
    ).toHaveAttribute("aria-expanded", "false");
  }
  await page.getByText("What am I paying for today?", { exact: true }).click();
  await expect(page.locator("details[open]")).toContainText(
    "does not automatically provision a Mechy engineering workspace",
  );
});

test("reduced motion renders a steady workbench", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const scene = page.locator(".makerspace-scene");
  await expect(scene).toBeVisible();
  await page.waitForTimeout(500);
  const before = await scene.screenshot();
  await page.waitForTimeout(250);
  const after = await scene.screenshot();
  expect(before.equals(after)).toBe(true);
  const canvas = scene.locator("canvas");
  const position = await canvas.getAttribute("data-camera-position");
  await page
    .locator(".journey-nav")
    .getByRole("button", { name: /Build/ })
    .click();
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Bring it all together in a working prototype.",
  );
  await expect(canvas).toHaveAttribute("data-camera-position", position!);
  const pose = await canvas.getAttribute("data-robot-pose");
  await page.mouse.move(200, 300);
  await page.waitForTimeout(200);
  await expect(canvas).toHaveAttribute("data-robot-pose", pose!);
  await expect(
    page.getByRole("button", { name: "Motion disabled by system preference" }),
  ).toBeDisabled();
});

test("WebGL failure retains a poster and working purchase controls", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      ...args: Parameters<typeof original>
    ) {
      if (String(args[0]).startsWith("webgl")) return null;
      return original.apply(this, args);
    } as typeof original;
  });
  await page.goto("/");
  await expect(page.locator(".makerspace-scene .scene-fallback")).toBeVisible();
  await expect(
    page.locator(".makerspace-scene .scene-fallback img"),
  ).toHaveJSProperty("naturalWidth", 1200);
  await page
    .locator(".journey-nav")
    .getByRole("button", { name: "Design", exact: true })
    .click();
  await expect(page.locator(".journey-chapter h2")).toHaveText(
    "Shape every detail with CAD and CAM.",
  );
  await expect(page.locator(".journey-copy")).toHaveCSS("opacity", "1");
  await page.getByRole("button", { name: "Get the demo", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});
