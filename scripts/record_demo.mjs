#!/usr/bin/env node

import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { createWriteStream } from "node:fs";
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { createServer } from "node:net";
import { homedir, tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";


const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const VIEWPORT = { width: 1440, height: 900 };
const FINAL_REPLY_TEXT = "Lurker, please answer: why does the API return 401?";
const CASES = [
  { sender: "Alex", text: "Let's meet at four tomorrow.", action: "SILENT" },
  {
    sender: "Lea",
    text: "Congratulations everyone—we made the hackathon finals! 🎉",
    action: "REACT",
  },
  { sender: "Sam", text: FINAL_REPLY_TEXT, action: "REPLY" },
];
const FROZEN_POLICY = {
  context_k: 3,
  reply_threshold: 0.2,
  react_threshold: 0.04,
};


function usage() {
  return `Usage: node scripts/record_demo.mjs [options]

Options:
  --mode preview|final       preview is safe MOCK mode (default: preview)
  --output-dir PATH          recording root (default: artifacts/demo-recordings)
  --pace NUMBER              timing multiplier from 0.05 to 2 (default: 1)
  --help                     show this help

Final mode is intentionally guarded. It requires these exact environment values:
  DEMO_ALLOW_ONE_BEDROCK_CALL=I_APPROVE_ONE_CALL
  MOCK_DECIDER=false
  BEDROCK_MAX_CALLS=1
  BEDROCK_ALLOWED_LATEST_TEXT=${JSON.stringify(FINAL_REPLY_TEXT)}
  AWS_REGION=us-east-2
  BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0

Do not run final mode without separate owner authorization for one Bedrock call.`;
}


function parseArgs(argv) {
  const options = {
    mode: "preview",
    outputDir: join(ROOT, "artifacts", "demo-recordings"),
    pace: 1,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === "--help") return { ...options, help: true };
    if (item === "--mode") options.mode = argv[++index];
    else if (item === "--output-dir") options.outputDir = resolve(argv[++index]);
    else if (item === "--pace") options.pace = Number(argv[++index]);
    else throw new Error(`Unknown argument: ${item}`);
  }
  if (!new Set(["preview", "final"]).has(options.mode)) {
    throw new Error("--mode must be preview or final");
  }
  if (!Number.isFinite(options.pace) || options.pace < 0.05 || options.pace > 2) {
    throw new Error("--pace must be between 0.05 and 2");
  }
  return options;
}


function requireFinalApproval(env) {
  const expected = {
    DEMO_ALLOW_ONE_BEDROCK_CALL: "I_APPROVE_ONE_CALL",
    MOCK_DECIDER: "false",
    BEDROCK_MAX_CALLS: "1",
    BEDROCK_ALLOWED_LATEST_TEXT: FINAL_REPLY_TEXT,
    AWS_REGION: "us-east-2",
    BEDROCK_MODEL_ID: "us.anthropic.claude-haiku-4-5-20251001-v1:0",
  };
  const failures = Object.entries(expected)
    .filter(([name, value]) => env[name] !== value)
    .map(([name]) => name);
  if (failures.length) {
    throw new Error(
      `Final recording authorization/configuration missing or incorrect: ${failures.join(", ")}`,
    );
  }
}


function timestamp() {
  return new Date().toISOString().replaceAll("-", "").replaceAll(":", "").replace(/\.\d{3}Z$/, "Z");
}


function sleep(milliseconds) {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, milliseconds));
}


async function pacedSleep(milliseconds, pace) {
  await sleep(Math.round(milliseconds * pace));
}


async function freePort() {
  const server = createServer();
  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : null;
  await new Promise((resolveClose, reject) => {
    server.close((error) => (error ? reject(error) : resolveClose()));
  });
  if (!port) throw new Error("Unable to reserve a local preview port");
  return port;
}


async function existingPython() {
  const candidate = join(ROOT, ".venv", "bin", "python");
  try {
    await access(candidate);
    return candidate;
  } catch {
    return "python3";
  }
}


async function fetchJson(url, options = undefined) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  return response.json();
}


async function waitForHealth(baseUrl, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError = "service did not respond";
  while (Date.now() < deadline) {
    try {
      const health = await fetchJson(`${baseUrl}/health`);
      if (health.status === "ok" && health.model_ready === true) return health;
      lastError = `health=${JSON.stringify(health)}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await sleep(500);
  }
  throw new Error(`Lurker did not become ready: ${lastError}`);
}


async function stopProcess(child) {
  if (!child || child.exitCode !== null) return;
  child.kill("SIGTERM");
  const exited = await Promise.race([
    new Promise((resolveExit) => child.once("exit", () => resolveExit(true))),
    sleep(5000).then(() => false),
  ]);
  if (!exited && child.exitCode === null) child.kill("SIGKILL");
}


async function waitForText(page, selector, expected, timeout = 180000) {
  await page.waitForFunction(
    ([target, value]) => document.querySelector(target)?.textContent?.trim() === value,
    [selector, expected],
    { timeout },
  );
}


async function sendCase(page, item) {
  const senderValue = item.sender === "Sam" ? "__third__" : item.sender;
  await page.locator("#sender").selectOption(senderValue);
  await page.locator("#message-input").fill(item.text);
  await page.locator("#send-button").click();
  await waitForText(page, "#decision-action", item.action);

  if (item.action === "REACT") {
    await page.locator('.reaction-chip[aria-label="Reaction 🎉"]').waitFor({
      state: "visible",
      timeout: 180000,
    });
  }
  if (item.action === "REPLY") {
    await page.locator(".message-row.is-agent .message-bubble").last().waitFor({
      state: "visible",
      timeout: 180000,
    });
  }

  return {
    sender: item.sender,
    text: item.text,
    expected_action: item.action,
    observed_action: (await page.locator("#decision-action").innerText()).trim(),
    confidence: (await page.locator("#confidence-value").innerText()).trim(),
    decider_latency: (await page.locator("#decision-latency").innerText()).trim(),
  };
}


async function sha256(path) {
  const payload = await readFile(path);
  return createHash("sha256").update(payload).digest("hex");
}


async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage());
    return;
  }
  if (options.mode === "final") requireFinalApproval(process.env);

  const runId = `${options.mode}-${timestamp()}`;
  const runDir = join(options.outputDir, runId);
  const rawVideoDir = join(runDir, "raw");
  const videoPath = join(runDir, `lurker-ai-${options.mode}.webm`);
  const manifestPath = join(runDir, "manifest.json");
  const serverLogPath = join(runDir, "server.log");
  const runtimeDir = await mkdtemp(join(tmpdir(), "lurker-demo-"));
  await mkdir(rawVideoDir, { recursive: true });

  const manifest = {
    schema_version: 1,
    run_id: runId,
    mode: options.mode,
    status: "running",
    submission_eligible: false,
    started_at: new Date().toISOString(),
    completed_at: null,
    elapsed_seconds: null,
    frozen_policy: FROZEN_POLICY,
    expected_actions: CASES.map(({ sender, text, action }) => ({ sender, text, action })),
    observed_actions: [],
    health: null,
    metrics_before: null,
    metrics_after: null,
    bedrock_call_delta: null,
    mock_banner_visible: null,
    reply_text: null,
    scene_timeline: [],
    recording_sequence_seconds: null,
    video: null,
    error: null,
  };

  let appProcess = null;
  let browser = null;
  let context = null;
  let page = null;
  let video = null;
  let recordingStarted = null;
  const started = Date.now();
  const markScene = (name) => {
    const seconds = recordingStarted === null
      ? 0
      : Number(((Date.now() - recordingStarted) / 1000).toFixed(3));
    manifest.scene_timeline.push({ name, seconds });
    console.log(`[scene ${seconds.toFixed(3)}s] ${name}`);
  };

  try {
    const port = await freePort();
    const baseUrl = `http://127.0.0.1:${port}`;
    const python = await existingPython();
    const serverLog = createWriteStream(serverLogPath, { flags: "a" });
    const serverEnv = {
      ...process.env,
      MOCK_DECIDER: options.mode === "preview" ? "true" : "false",
      CONTEXT_K: "3",
      REPLY_THRESHOLD: "0.20",
      REACT_THRESHOLD: "0.04",
      FORCE_REPLY_ON_MENTION: "false",
      LURKER_DATA_DIR: join(runtimeDir, "data"),
      LURKER_RESULTS_DIR: join(ROOT, "results"),
      AWS_EC2_METADATA_DISABLED: "true",
      PYTHONPATH: ROOT,
    };
    if (options.mode === "preview") {
      for (const name of [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
      ]) {
        delete serverEnv[name];
      }
    }
    appProcess = spawn(
      python,
      ["-m", "uvicorn", "src.lurker.api:app", "--host", "127.0.0.1", "--port", String(port)],
      { cwd: ROOT, env: serverEnv, stdio: ["ignore", "pipe", "pipe"] },
    );
    appProcess.stdout.pipe(serverLog);
    appProcess.stderr.pipe(serverLog);

    const health = await waitForHealth(baseUrl, options.mode === "preview" ? 30000 : 300000);
    manifest.health = health;
    const expectedMode = options.mode === "preview" ? "mock" : "real";
    if (health.decider_mode !== expectedMode) {
      throw new Error(`Expected ${expectedMode} Decider, received ${health.decider_mode}`);
    }

    const about = await fetchJson(`${baseUrl}/api/about`);
    const observedPolicy = about.policy;
    if (
      observedPolicy.context_k !== FROZEN_POLICY.context_k
      || observedPolicy.reply_threshold !== FROZEN_POLICY.reply_threshold
      || observedPolicy.react_threshold !== FROZEN_POLICY.react_threshold
    ) {
      throw new Error(`Frozen policy mismatch: ${JSON.stringify(observedPolicy)}`);
    }

    manifest.metrics_before = (await fetchJson(`${baseUrl}/api/metrics`)).counters;
    browser = await chromium.launch({ channel: "chrome", headless: true });
    context = await browser.newContext({
      viewport: VIEWPORT,
      recordVideo: { dir: rawVideoDir, size: VIEWPORT },
      colorScheme: "light",
    });
    page = await context.newPage();
    video = page.video();
    recordingStarted = Date.now();
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.locator('#connection-status[data-state="online"]').waitFor({ state: "visible" });
    markScene("hook_ready");

    manifest.mock_banner_visible = await page.locator("#mock-banner").isVisible();
    if (options.mode === "preview" && !manifest.mock_banner_visible) {
      throw new Error("Preview recording must display the MOCK banner");
    }
    if (options.mode === "final" && manifest.mock_banner_visible) {
      throw new Error("Final recording refuses to capture a MOCK banner");
    }

    await pacedSleep(4000, options.pace);
    await page.locator("#about-tab").click();
    await page.locator("#about-panel").waitFor({ state: "visible" });
    markScene("about");
    await pacedSleep(7000, options.pace);
    await page.locator("#live-tab").click();

    for (const item of CASES) {
      const observed = await sendCase(page, item);
      manifest.observed_actions.push(observed);
      markScene(item.action.toLowerCase());
      await pacedSleep(item.action === "REPLY" ? 9000 : 7000, options.pace);
    }

    manifest.reply_text = (
      await page.locator(".message-row.is-agent .message-bubble").last().innerText()
    ).trim();
    markScene("measured_behavior");
    await pacedSleep(6000, options.pace);

    await page.goto(`${baseUrl}/assets/pattern.html`, { waitUntil: "networkidle" });
    await page.locator("#pattern-title").waitFor({ state: "visible" });
    markScene("reusable_pattern");
    await pacedSleep(9000, options.pace);

    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.locator('#connection-status[data-state="online"]').waitFor({ state: "visible" });
    await page.locator("#evaluation-tab").click();
    await page.locator("#evaluation-content").waitFor({ state: "visible" });
    await waitForText(page, "#evaluation-status", "Published NO-GO", 30000);
    markScene("honest_close");
    await pacedSleep(11000, options.pace);

    manifest.metrics_after = (await fetchJson(`${baseUrl}/api/metrics`)).counters;
    manifest.bedrock_call_delta =
      manifest.metrics_after.bedrock_calls_made - manifest.metrics_before.bedrock_calls_made;
    const expectedCalls = options.mode === "preview" ? 0 : 1;
    if (manifest.bedrock_call_delta !== expectedCalls) {
      throw new Error(
        `Expected ${expectedCalls} Bedrock calls, observed ${manifest.bedrock_call_delta}`,
      );
    }
    if (manifest.metrics_after.errors !== 0) {
      throw new Error(`Runtime recorded ${manifest.metrics_after.errors} errors`);
    }

    manifest.recording_sequence_seconds = Number(
      ((Date.now() - recordingStarted) / 1000).toFixed(3),
    );
    markScene("capture_complete");
    if (manifest.recording_sequence_seconds >= 165) {
      throw new Error(
        `Recording sequence exceeded the 2:45 target: ${manifest.recording_sequence_seconds}s`,
      );
    }

    await context.close();
    context = null;
    await video.saveAs(videoPath);
    const videoStats = await stat(videoPath);
    manifest.video = {
      path: videoPath,
      bytes: videoStats.size,
      sha256: await sha256(videoPath),
      viewport: VIEWPORT,
      silent: true,
    };
    manifest.status = "pass";
    manifest.submission_eligible = options.mode === "final";
  } catch (error) {
    manifest.status = "fail";
    manifest.error = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
    throw error;
  } finally {
    if (context) {
      try {
        await context.close();
      } catch {
        // Preserve the original recorder failure.
      }
    }
    if (browser) await browser.close();
    await stopProcess(appProcess);
    manifest.completed_at = new Date().toISOString();
    manifest.elapsed_seconds = Number(((Date.now() - started) / 1000).toFixed(3));
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    await rm(runtimeDir, { recursive: true, force: true });
    console.log(`Manifest: ${manifestPath}`);
    if (manifest.video) console.log(`Video: ${manifest.video.path}`);
  }
}


main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
