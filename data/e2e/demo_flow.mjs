/**
 * E2E browser demo for SIH26054 — follows docs/demo_script.md / README flow:
 *   start mission -> charts stream -> inject fault -> detection -> stop
 *   -> replay 5x -> reports page
 * Drives the real UI (no API shortcuts) with puppeteer-core + installed Chrome.
 */
import puppeteer from "puppeteer-core";
import { mkdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const BASE = "http://localhost:3000";
const SHOTS_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../docs/screenshots/demo");
mkdirSync(SHOTS_DIR, { recursive: true });

const CHROME_CANDIDATES = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
];
const CHROME = CHROME_CANDIDATES.find((p) => existsSync(p));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (s) => console.log(`[demo ${new Date().toISOString().slice(11, 19)}] ${s}`);

const pageErrors = [];

async function waitForText(page, text, timeoutMs = 20000, rootSel = "body") {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const found = await page.evaluate(
      ({ rootSel, text }) => {
        const root = document.querySelector(rootSel);
        return root ? root.textContent.includes(text) : false;
      },
      { rootSel, text }
    );
    if (found) return true;
    await sleep(300);
  }
  throw new Error(`timeout waiting for text "${text}"`);
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(SHOTS_DIR, name) });
  log(`screenshot: ${name}`);
}

/** Set a React-controlled select (by index among panel selects) and fire change events. */
async function setSelect(page, index, value) {
  await page.evaluate(
    ({ index, value }) => {
      const el = document.querySelectorAll(".controls-panel select")[index];
      const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set;
      setter.call(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    },
    { index, value }
  );
}

async function setInputValue(page, index, value) {
  await page.evaluate(
    ({ index, value }) => {
      const el = document.querySelectorAll(".controls-panel input")[index];
      const proto = el.type === "range" ? window.HTMLInputElement.prototype : window.HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
      setter.call(el, String(value));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    },
    { index, value }
  );
}

/** Click a button by exact visible text within .controls-panel (re-queries fresh). */
async function clickButton(page, text) {
  const ok = await page.evaluate((text) => {
    const btn = [...document.querySelectorAll(".controls-panel button")].find((b) => b.textContent.trim() === text && !b.disabled);
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  }, text);
  if (!ok) throw new Error(`button not clickable: "${text}"`);
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  defaultViewport: { width: 1500, height: 1100 },
});

try {
  const page = await browser.newPage();
  page.on("pageerror", (err) => pageErrors.push(String(err)));

  // ---------- Stage -1: clean state from any previous run ----------
  for (const ep of ["/api/v1/simulation/stop", "/api/v1/replay/stop"]) {
    await fetch(BASE + ep, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ engine_id: "ENG-001" }),
    }).catch(() => {});
  }
  await sleep(2000);
  log("cleanup done (no mission/replay running)");

  // ---------- Stage 0: dashboard up, backend + WS connected ----------
  log("opening dashboard");
  await page.goto(BASE, { waitUntil: "networkidle2", timeout: 30000 });
  await waitForText(page, "BACKEND OK");
  await waitForText(page, "LIVE");
  log("backend OK + websocket LIVE");

  // ---------- Stage 1: configure + start mission ----------
  await setSelect(page, 0, "hot_weather"); // profile
  await setInputValue(page, 0, 180); // duration input
  await clickButton(page, "Start Mission");
  log("clicked Start Mission");
  await waitForText(page, "MISSION ACTIVE", 15000);
  const missionId = await page.evaluate(() => {
    const cards = [...document.querySelectorAll(".twin-meta .stat-card")];
    const c = cards.find((el) => el.querySelector(".stat-label")?.textContent === "Mission");
    const m = c?.querySelector(".stat-value")?.textContent.match(/M-[0-9A-F]{8}/);
    return m ? m[0] : null;
  });
  if (!missionId) throw new Error("could not read mission id from twin card");
  log(`mission started: ${missionId}`);
  await sleep(1500);
  await shot(page, "01_mission_started.png");

  // ---------- Stage 2: charts stream ----------
  await sleep(15000);
  const streamStats = await page.evaluate(() => ({
    dataCurves: [...document.querySelectorAll(".recharts-line-curve")].filter((c) => (c.getAttribute("d") || "").length > 20).length,
    telemetryRows: document.querySelectorAll(".grid-bottom table tbody tr").length,
    live: document.body.textContent.includes("LIVE"),
  }));
  log(`streaming: dataCurves=${streamStats.dataCurves} telemetryRows=${streamStats.telemetryRows} live=${streamStats.live}`);
  if (streamStats.dataCurves < 5) throw new Error("charts look empty");
  if (streamStats.telemetryRows < 3) throw new Error("telemetry table not filling");
  await shot(page, "02_charts_streaming.png");

  // ---------- Stage 3: inject fault ----------
  await setSelect(page, 1, "overheating"); // fault type
  await setInputValue(page, 1, 0.8); // severity slider
  await setInputValue(page, 2, 60); // fault duration
  await clickButton(page, "Inject Fault");
  log("clicked Inject Fault");
  await waitForText(page, "injected", 8000, ".toasts");
  log("fault injection toast confirmed");
  await shot(page, "03_fault_injected.png");

  // ---------- Stage 4: watch detection ----------
  await waitForText(page, "overheating", 25000, ".alerts");
  log("fault detected in alerts feed");
  const detectionState = await page.evaluate(() => {
    const badges = [...document.querySelectorAll(".status-badge-row .badge")].map((b) => b.textContent.trim());
    return { badges, alertItems: document.querySelectorAll(".alerts li").length };
  });
  log(`status badges: ${detectionState.badges.join(" | ")} | alert items: ${detectionState.alertItems}`);
  await shot(page, "04_fault_detected.png");

  // ---------- Stage 5: stop mission ----------
  await clickButton(page, "Stop Mission");
  log("clicked Stop Mission");
  await waitForText(page, "stopped", 10000, ".toasts");
  await waitForText(page, "IDLE", 10000);
  log("mission stopped, report generated");

  // ---------- Stage 6: replay our mission at 5x ----------
  await sleep(1500); // let mission list refresh
  await setSelect(page, 2, missionId); // replay mission select
  const replaySel = await page.evaluate(() => document.querySelectorAll(".controls-panel select")[2]?.value);
  if (replaySel !== missionId) throw new Error(`replay select = ${replaySel}, expected ${missionId}`);
  await clickButton(page, "Replay (5x)");
  log("clicked Replay (5x)");
  await waitForText(page, "Replaying", 8000, ".toasts");
  await sleep(9000); // let it fill some series
  await shot(page, "05_replay.png");
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll(".controls-panel button")].find((b) => b.textContent.trim() === "Stop" && !b.disabled);
    btn?.click();
  });
  log("replay stopped");

  // ---------- Stage 7: reports page ----------
  await page.goto(`${BASE}/reports?mission=${missionId}`, { waitUntil: "networkidle2", timeout: 30000 });
  await waitForText(page, "Avg Health Index", 15000, ".report");
  const reportStats = await page.evaluate(() => document.querySelector(".report")?.textContent ?? "");
  const hasFault = reportStats.includes("overheating");
  const hasAdvisory = reportStats.includes("[") && reportStats.includes("advisory") || reportStats.includes("Cylinder");
  log(`report: fault lines mention overheating=${hasFault}, advisories present=${hasAdvisory}`);
  await shot(page, "06_report.png");

  // ---------- verdict ----------
  if (pageErrors.length > 0) {
    log(`PAGE ERRORS (${pageErrors.length}): ${pageErrors.slice(0, 3).join(" ;; ")}`);
    process.exitCode = 2;
  } else {
    log(`E2E DEMO PASSED — mission ${missionId}: start → stream → fault → detection → stop → replay → report`);
  }
} catch (err) {
  log(`E2E DEMO FAILED: ${err.message}`);
  try {
    const page = (await browser.pages())[0];
    await shot(page, "99_failure.png");
  } catch {}
  process.exitCode = 1;
} finally {
  await browser.close();
}
