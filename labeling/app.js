const state = {
  annotator: null,
  dataset: null,
  scenarios: [],
  labels: {},
  index: 0,
};

const allowedLabels = new Set(["SILENT", "REACT", "REPLY"]);
const setup = document.querySelector("#setup");
const workspace = document.querySelector("#workspace");
const conversation = document.querySelector("#conversation");
const statusLine = document.querySelector("#status");

function storageKey() {
  return `lurker-human-labels:${state.dataset.id}:${state.annotator}:${state.dataset.storage_version}`;
}

function exportFilename() {
  return `${state.dataset.export_prefix}_${state.annotator}.csv`;
}

function loadSavedLabels() {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey()) || "{}");
    state.labels = Object.fromEntries(
      Object.entries(parsed).filter(([, value]) => allowedLabels.has(value)),
    );
  } catch {
    state.labels = {};
  }
}

function stableHash(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function orderForEvaluator(scenarios, annotator) {
  return [...scenarios].sort((left, right) => {
    const leftHash = stableHash(`${state.dataset.id}:${annotator}:${left.id}`);
    const rightHash = stableHash(`${state.dataset.id}:${annotator}:${right.id}`);
    return leftHash - rightHash || left.id.localeCompare(right.id);
  });
}

function saveLabels() {
  localStorage.setItem(storageKey(), JSON.stringify(state.labels));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMessage(message, latest = false) {
  return `<article class="message${latest ? " latest" : ""}">
    <span class="sender">${escapeHtml(message.sender)}${latest ? " · latest message" : ""}</span>
    <p>${escapeHtml(message.text)}</p>
  </article>`;
}

function render() {
  const scenario = state.scenarios[state.index];
  if (!scenario) return;
  const history = scenario.history.length
    ? scenario.history.map((message) => renderMessage(message)).join("")
    : '<p class="empty-history">No earlier messages in this scenario</p>';
  conversation.innerHTML = `${history}${renderMessage(scenario.message, true)}`;

  document.querySelector("#position").textContent = `Scenario ${state.index + 1} of ${state.scenarios.length}`;
  document.querySelector("#previous").disabled = state.index === 0;
  document.querySelector("#next").disabled = state.index === state.scenarios.length - 1;

  const completed = Object.keys(state.labels).filter((id) => state.scenarios.some((item) => item.id === id)).length;
  document.querySelector("#progress-text").textContent = `${completed} of ${state.scenarios.length} labeled`;
  const progress = document.querySelector(".progress-track");
  progress.setAttribute("aria-valuemax", String(state.scenarios.length));
  progress.setAttribute("aria-valuenow", String(completed));
  document.querySelector("#progress-fill").style.width = `${(completed / state.scenarios.length) * 100}%`;
  document.querySelector("#export").disabled = completed !== state.scenarios.length;

  document.querySelectorAll(".choice").forEach((button) => {
    const selected = button.dataset.choice === state.labels[scenario.id];
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

function selectLabel(label) {
  const scenario = state.scenarios[state.index];
  state.labels[scenario.id] = label;
  saveLabels();
  render();
  if (state.index < state.scenarios.length - 1) {
    window.setTimeout(() => {
      state.index += 1;
      render();
    }, 180);
  }
}

async function chooseSlot(annotator) {
  state.annotator = annotator;
  state.scenarios = orderForEvaluator(state.scenarios, annotator);
  state.index = 0;
  loadSavedLabels();
  setup.classList.add("hidden");
  workspace.classList.remove("hidden");
  document.querySelector("#evaluator-name").textContent = `Evaluator ${annotator.slice(1)} · answers private`;
  statusLine.textContent = Object.keys(state.labels).length ? "Saved progress restored." : "Ready to label.";
  render();
}

function csvCell(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function exportCsv() {
  const rows = ["id,label", ...state.scenarios.map((item) => `${csvCell(item.id)},${csvCell(state.labels[item.id])}`)];
  const blob = new Blob([`${rows.join("\n")}\n`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = exportFilename();
  link.click();
  URL.revokeObjectURL(url);
  statusLine.textContent = `Exported ${exportFilename()}. Send this file to the project owner.`;
}

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.shift()?.replaceAll('"', "").trim() !== "id,label") {
    throw new Error("CSV must have id,label columns.");
  }
  const knownIds = new Set(state.scenarios.map((item) => item.id));
  const labels = {};
  for (const line of lines) {
    const match = line.match(/^"?([^",]+)"?,"?([^",]+)"?$/);
    if (!match || !knownIds.has(match[1]) || !allowedLabels.has(match[2].toUpperCase())) {
      throw new Error("CSV contains an unknown scenario or label.");
    }
    labels[match[1]] = match[2].toUpperCase();
  }
  return labels;
}

document.querySelectorAll(".slot").forEach((button) => {
  button.addEventListener("click", () => chooseSlot(button.dataset.slot));
});
document.querySelectorAll(".choice").forEach((button) => {
  button.addEventListener("click", () => selectLabel(button.dataset.choice));
});
document.querySelector("#previous").addEventListener("click", () => { state.index -= 1; render(); });
document.querySelector("#next").addEventListener("click", () => { state.index += 1; render(); });
document.querySelector("#export").addEventListener("click", exportCsv);
document.querySelector("#change-slot").addEventListener("click", () => {
  state.annotator = null;
  state.labels = {};
  state.index = 0;
  state.scenarios.sort((left, right) => left.id.localeCompare(right.id));
  workspace.classList.add("hidden");
  setup.classList.remove("hidden");
});
document.querySelector("#reset").addEventListener("click", () => {
  if (window.confirm("Clear every saved answer for this evaluator slot?")) {
    localStorage.removeItem(storageKey());
    state.labels = {};
    state.index = 0;
    statusLine.textContent = "This evaluator slot has been cleared.";
    render();
  }
});
document.querySelector("#import-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    state.labels = parseCsv(await file.text());
    saveLabels();
    statusLine.textContent = `Imported ${Object.keys(state.labels).length} answers.`;
    render();
  } catch (error) {
    statusLine.textContent = error.message;
  }
  event.target.value = "";
});
document.addEventListener("keydown", (event) => {
  if (workspace.classList.contains("hidden") || event.target.matches("input")) return;
  const labelByKey = { "1": "SILENT", "2": "REACT", "3": "REPLY" };
  if (labelByKey[event.key]) selectLabel(labelByKey[event.key]);
});

fetch("/api/scenarios", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error("Could not load scenarios.");
    return response.json();
  })
  .then((payload) => {
    state.dataset = payload.dataset;
    state.scenarios = [...payload.scenarios].sort((left, right) => left.id.localeCompare(right.id));
    document.querySelectorAll(".slot").forEach((button) => {
      button.querySelector("small").textContent = `Export: ${state.dataset.export_prefix}_${button.dataset.slot}.csv`;
    });
    document.querySelector("#progress-text").textContent = `0 of ${state.scenarios.length} labeled`;
    const requested = new URLSearchParams(window.location.search).get("annotator");
    if (["a1", "a2", "a3"].includes(requested)) chooseSlot(requested);
  })
  .catch((error) => {
    setup.innerHTML = `<h2>Could not start</h2><p>${escapeHtml(error.message)} Restart the local labeling server and refresh this page.</p>`;
  });
