"use strict";

const elements = {
  aboutContext: document.querySelector("#about-context"),
  aboutError: document.querySelector("#about-error-policy"),
  aboutLowConfidence: document.querySelector("#about-low-confidence"),
  aboutMention: document.querySelector("#about-mention"),
  aboutOptions: document.querySelector("#about-options"),
  aboutPanel: document.querySelector("#about-panel"),
  aboutQuestion: document.querySelector("#about-question"),
  aboutReactThreshold: document.querySelector("#about-react-threshold"),
  aboutReplyThreshold: document.querySelector("#about-reply-threshold"),
  aboutTab: document.querySelector("#about-tab"),
  announcer: document.querySelector("#announcer"),
  confidenceFill: document.querySelector("#confidence-fill"),
  confidenceValue: document.querySelector("#confidence-value"),
  connectionStatus: document.querySelector("#connection-status"),
  countAvoided: document.querySelector("#count-avoided"),
  countBedrock: document.querySelector("#count-bedrock"),
  countMessages: document.querySelector("#count-messages"),
  countReact: document.querySelector("#count-react"),
  countReply: document.querySelector("#count-reply"),
  countSilent: document.querySelector("#count-silent"),
  decisionAction: document.querySelector("#decision-action"),
  decisionLatency: document.querySelector("#decision-latency"),
  decisionLogBody: document.querySelector("#decision-log-body"),
  decisionPolicy: document.querySelector("#decision-policy"),
  decisionTime: document.querySelector("#decision-time"),
  evaluationAccuracy: document.querySelector("#evaluation-accuracy"),
  evaluationAccuracyCount: document.querySelector("#evaluation-accuracy-count"),
  evaluationBaselineBody: document.querySelector("#evaluation-baseline-body"),
  evaluationBaselineNote: document.querySelector("#evaluation-baseline-note"),
  evaluationBoundaryText: document.querySelector("#evaluation-boundary-text"),
  evaluationCalibrationBody: document.querySelector("#evaluation-calibration-body"),
  evaluationContent: document.querySelector("#evaluation-content"),
  evaluationContextBody: document.querySelector("#evaluation-context-body"),
  evaluationEnvironment: document.querySelector("#evaluation-environment"),
  evaluationGenerated: document.querySelector("#evaluation-generated"),
  evaluationInterruption: document.querySelector("#evaluation-interruption"),
  evaluationInterruptionCount: document.querySelector("#evaluation-interruption-count"),
  evaluationMissedHelp: document.querySelector("#evaluation-missed-help"),
  evaluationMissedHelpCount: document.querySelector("#evaluation-missed-help-count"),
  evaluationPanel: document.querySelector("#evaluation-panel"),
  evaluationPolicy: document.querySelector("#evaluation-policy"),
  evaluationPrimaryStatus: document.querySelector("#evaluation-primary-status"),
  evaluationSampleNote: document.querySelector("#evaluation-sample-note"),
  evaluationState: document.querySelector("#evaluation-state"),
  evaluationStatus: document.querySelector("#evaluation-status"),
  evaluationTab: document.querySelector("#evaluation-tab"),
  form: document.querySelector("#composer"),
  inlineAlert: document.querySelector("#inline-alert"),
  livePanel: document.querySelector("#live-panel"),
  liveTab: document.querySelector("#live-tab"),
  messageInput: document.querySelector("#message-input"),
  messageList: document.querySelector("#message-list"),
  mockBanner: document.querySelector("#mock-banner"),
  modeChip: document.querySelector("#mode-chip"),
  rawChoice: document.querySelector("#raw-choice"),
  resetButton: document.querySelector("#reset-button"),
  sendButton: document.querySelector("#send-button"),
  sender: document.querySelector("#sender"),
  thirdName: document.querySelector("#third-name"),
  thirdOption: document.querySelector("#third-sender-option"),
};

const state = {
  socket: null,
  reconnectAttempts: 0,
  reconnectTimer: null,
  pendingMessage: null,
  pendingTimer: null,
  messages: new Map(),
  queuedReactions: new Map(),
  reactionKeys: new Set(),
  decisions: [],
  counters: null,
  evaluationLoaded: false,
  evaluationLoading: false,
};

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function announce(message) {
  elements.announcer.textContent = "";
  window.setTimeout(() => { elements.announcer.textContent = message; }, 10);
}

function showAlert(message) {
  elements.inlineAlert.textContent = message;
  elements.inlineAlert.hidden = false;
}

function clearAlert() {
  elements.inlineAlert.hidden = true;
  elements.inlineAlert.textContent = "";
}

function setConnection(stateName, label) {
  elements.connectionStatus.dataset.state = stateName;
  elements.connectionStatus.lastElementChild.textContent = label;
}

function selectedSender() {
  if (elements.sender.value !== "__third__") return elements.sender.value;
  return elements.thirdName.value.trim() || "Sam";
}

function updateComposerState() {
  const connected = state.socket && state.socket.readyState === WebSocket.OPEN;
  const hasText = elements.messageInput.value.trim().length > 0;
  elements.messageInput.disabled = !connected;
  elements.sendButton.disabled = !connected || !hasText || Boolean(state.pendingMessage);
  elements.resetButton.disabled = !connected;
}

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit", second: "2-digit" }).format(date);
}

function formatConfidence(value) {
  const confidence = Number(value);
  return Number.isFinite(confidence) ? `${(confidence * 100).toFixed(1)}%` : "—";
}

function formatLatency(value) {
  const latency = Number(value);
  return Number.isFinite(latency) ? `${latency.toFixed(2)} ms` : "—";
}

function showEmptyChat() {
  const empty = makeElement("div", "empty-chat");
  empty.dataset.emptyChat = "true";
  empty.append(
    makeElement("span", "empty-glyph", "•••"),
    makeElement("h2", "", "Start a conversation"),
    makeElement("p", "", "Switch between teammates and watch Lurker decide whether to stay quiet, react, or reply."),
  );
  empty.firstElementChild.setAttribute("aria-hidden", "true");
  elements.messageList.append(empty);
}

function appendReaction(messageId, emoji) {
  const reactionKey = `${messageId}:${emoji}`;
  if (state.reactionKeys.has(reactionKey)) return;
  const message = state.messages.get(messageId);
  if (!message) {
    const queued = state.queuedReactions.get(messageId) || [];
    if (!queued.includes(emoji)) queued.push(emoji);
    state.queuedReactions.set(messageId, queued);
    return;
  }
  state.reactionKeys.add(reactionKey);
  const chip = makeElement("span", "reaction-chip", emoji);
  chip.setAttribute("aria-label", `Reaction ${emoji}`);
  message.reactions.append(chip);
  announce(`Lurker reacted ${emoji} to ${message.data.sender}'s message.`);
}

function renderChatMessage(event) {
  if (state.messages.has(event.id)) return;
  const empty = elements.messageList.querySelector("[data-empty-chat]");
  if (empty) empty.remove();

  const row = makeElement("article", `message-row${event.is_agent ? " is-agent" : ""}`);
  row.dataset.messageId = event.id;
  const avatar = makeElement("div", "message-avatar", event.is_agent ? "L" : String(event.sender).slice(0, 1).toUpperCase());
  avatar.setAttribute("aria-hidden", "true");
  const body = makeElement("div", "message-body");
  const meta = makeElement("p", "message-meta");
  meta.append(makeElement("strong", "", event.sender), makeElement("span", "", formatTime(event.ts)));
  const bubble = makeElement("p", "message-bubble", event.text);
  const reactions = makeElement("div", "reaction-strip");
  reactions.setAttribute("aria-label", `Reactions to ${event.sender}'s message`);
  body.append(meta, bubble, reactions);
  row.append(avatar, body);
  elements.messageList.append(row);
  state.messages.set(event.id, { data: event, row, reactions });

  const queued = state.queuedReactions.get(event.id) || [];
  queued.forEach((emoji) => appendReaction(event.id, emoji));
  state.queuedReactions.delete(event.id);

  if (
    state.pendingMessage &&
    !event.is_agent &&
    event.sender === state.pendingMessage.sender &&
    event.text === state.pendingMessage.text
  ) {
    window.clearTimeout(state.pendingTimer);
    state.pendingMessage = null;
    elements.messageInput.value = "";
    elements.messageInput.style.height = "auto";
    updateComposerState();
    elements.messageInput.focus();
  }

  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

function normalizedDecision(event) {
  const message = state.messages.get(event.message_id)?.data;
  return {
    ...event,
    sender: event.sender || message?.sender || "Unknown",
    text: event.text || message?.text || "Message unavailable",
  };
}

function mergeDecisions(...groups) {
  const byMessage = new Map();
  groups.flat().forEach((decision) => {
    const normalized = normalizedDecision(decision);
    const existing = byMessage.get(normalized.message_id);
    if (!existing || new Date(normalized.ts).getTime() >= new Date(existing.ts).getTime()) {
      byMessage.set(normalized.message_id, normalized);
    }
  });
  return [...byMessage.values()]
    .sort((left, right) => new Date(right.ts).getTime() - new Date(left.ts).getTime())
    .slice(0, 50);
}

function acknowledgePendingDecision(decision) {
  if (
    !state.pendingMessage ||
    decision.sender !== state.pendingMessage.sender ||
    decision.text !== state.pendingMessage.text
  ) return;
  window.clearTimeout(state.pendingTimer);
  state.pendingMessage = null;
  elements.messageInput.value = "";
  elements.messageInput.style.height = "auto";
  updateComposerState();
}

function renderDecisionHero(decision) {
  if (!decision) {
    elements.decisionAction.textContent = "—";
    elements.decisionAction.removeAttribute("data-action");
    elements.decisionTime.textContent = "No decisions yet";
    elements.confidenceValue.textContent = "—";
    elements.confidenceFill.style.width = "0%";
    elements.rawChoice.textContent = "—";
    elements.decisionLatency.textContent = "—";
    elements.decisionPolicy.textContent = "—";
    return;
  }
  elements.decisionAction.textContent = decision.final_action;
  elements.decisionAction.dataset.action = decision.final_action;
  elements.decisionTime.textContent = formatTime(decision.ts);
  elements.confidenceValue.textContent = formatConfidence(decision.confidence);
  elements.confidenceFill.style.width = `${Math.max(0, Math.min(100, Number(decision.confidence) * 100))}%`;
  elements.rawChoice.textContent = decision.raw_choice || "ERROR";
  elements.decisionLatency.textContent = formatLatency(decision.decider_latency_ms);
  elements.decisionPolicy.textContent = decision.downgraded ? `Downgraded · ${decision.reason}` : decision.reason;
}

function renderDecisionLog() {
  elements.decisionLogBody.replaceChildren();
  if (!state.decisions.length) {
    const row = makeElement("tr", "empty-row");
    const cell = makeElement("td", "", "Decisions will appear here.");
    cell.colSpan = 4;
    row.append(cell);
    elements.decisionLogBody.append(row);
    return;
  }

  state.decisions.slice(0, 50).forEach((decision) => {
    const row = document.createElement("tr");
    const messageCell = document.createElement("td");
    const message = makeElement("div", "log-message");
    message.append(
      makeElement("strong", "", `${decision.sender} · ${formatTime(decision.ts)}`),
      makeElement("span", "", decision.text),
    );
    messageCell.append(message);
    const rawCell = makeElement("td", "", decision.raw_choice || "ERROR");
    const confidenceCell = makeElement("td", "", formatConfidence(decision.confidence));
    const finalCell = document.createElement("td");
    const pill = makeElement("span", "action-pill", decision.final_action);
    pill.dataset.action = decision.final_action;
    finalCell.append(pill);
    row.append(messageCell, rawCell, confidenceCell, finalCell);
    elements.decisionLogBody.append(row);
  });
}

function recordDecision(event) {
  const decision = normalizedDecision(event);
  state.decisions = mergeDecisions([decision], state.decisions);
  acknowledgePendingDecision(decision);
  renderDecisionHero(decision);
  renderDecisionLog();
  announce(`Lurker chose ${decision.final_action} for ${decision.sender}'s message.`);
}

async function reconcileAfterReconnect() {
  const [metricsResult, decisionsResult] = await Promise.allSettled([
    loadJson("/api/metrics"),
    loadJson("/api/decisions?limit=50"),
  ]);
  if (metricsResult.status === "fulfilled") renderCounters(metricsResult.value.counters);
  if (decisionsResult.status === "fulfilled") {
    state.decisions = mergeDecisions(decisionsResult.value, state.decisions);
    state.decisions.forEach(acknowledgePendingDecision);
    renderDecisionHero(state.decisions[0]);
    renderDecisionLog();
  }
  if (metricsResult.status === "rejected" || decisionsResult.status === "rejected") {
    showAlert("The connection is back, but recent activity could not be fully synchronized.");
    return false;
  }
  return true;
}

function renderCounters(counters) {
  state.counters = counters;
  elements.countMessages.textContent = counters.messages_read;
  elements.countSilent.textContent = counters.silent;
  elements.countReact.textContent = counters.react;
  elements.countReply.textContent = counters.reply;
  elements.countBedrock.textContent = counters.bedrock_calls_made;
  elements.countAvoided.textContent = counters.bedrock_calls_avoided_vs_every_message;
}

function renderAbout(about) {
  elements.aboutQuestion.textContent = about.question;
  elements.aboutOptions.replaceChildren();
  about.options.forEach((option) => {
    const item = makeElement("article", "about-option");
    item.dataset.action = option.action;
    item.append(makeElement("strong", "", option.action), makeElement("p", "", option.description));
    elements.aboutOptions.append(item);
  });
  elements.aboutContext.textContent = `Last ${about.policy.context_k} messages`;
  elements.aboutReplyThreshold.textContent = Number(about.policy.reply_threshold).toFixed(2);
  elements.aboutReactThreshold.textContent = Number(about.policy.react_threshold).toFixed(2);
  elements.aboutMention.textContent = about.policy.force_reply_on_mention ? "Enabled" : "Disabled";
  elements.aboutLowConfidence.textContent = about.policy.low_confidence;
  elements.aboutError.textContent = about.policy.error;
}

function handleSocketEvent(event) {
  if (!event || typeof event.type !== "string") return;
  if (event.type === "chat") renderChatMessage(event);
  else if (event.type === "reaction") appendReaction(event.message_id, event.emoji);
  else if (event.type === "decision") recordDecision(event);
  else if (event.type === "metrics") renderCounters(event.counters);
  else if (event.type === "error") showAlert("The message was rejected. Check the sender and message, then try again.");
}

function connectSocket() {
  window.clearTimeout(state.reconnectTimer);
  setConnection("loading", state.reconnectAttempts ? "Reconnecting" : "Connecting");
  updateComposerState();
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
  state.socket = socket;

  socket.addEventListener("open", async () => {
    const reconnected = state.reconnectAttempts > 0;
    state.reconnectAttempts = 0;
    clearAlert();
    setConnection("online", "Live connection");
    updateComposerState();
    if (reconnected) {
      const synchronized = await reconcileAfterReconnect();
      if (synchronized) announce("Reconnected and synchronized with the Lurker decision service.");
    } else {
      announce("Connected to the Lurker decision service.");
    }
  });

  socket.addEventListener("message", (message) => {
    try {
      handleSocketEvent(JSON.parse(message.data));
    } catch (_error) {
      showAlert("Lurker received an unreadable live event. Refresh if the issue continues.");
    }
  });

  socket.addEventListener("close", () => {
    if (state.socket !== socket) return;
    setConnection("offline", "Connection lost");
    updateComposerState();
    if (state.reconnectAttempts >= 6) {
      showAlert("The live connection could not be restored. Refresh the page to try again.");
      return;
    }
    const delay = Math.min(8000, 1000 * (2 ** state.reconnectAttempts));
    state.reconnectAttempts += 1;
    state.reconnectTimer = window.setTimeout(connectSocket, delay);
  });

  socket.addEventListener("error", () => socket.close());
}

async function loadJson(path, options) {
  const response = await fetch(path, { cache: "no-store", ...options });
  if (!response.ok) {
    const error = new Error(`${path} returned ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function evaluationRate(metric) {
  const rate = metric?.rate;
  return typeof rate === "number" && Number.isFinite(rate) ? `${(rate * 100).toFixed(1)}%` : "N/A";
}

function evaluationCount(metric) {
  const numerator = Number(metric?.numerator);
  const denominator = Number(metric?.denominator);
  if (!Number.isInteger(numerator) || !Number.isInteger(denominator)) return "Counts unavailable";
  return `${numerator}/${denominator}`;
}

function metricPasses(metrics, criteria) {
  const accuracy = metrics.accuracy?.rate;
  const interruption = metrics.unnecessary_interruption_rate?.rate;
  const missedHelp = metrics.missed_help_rate?.rate;
  return (
    Number(metrics.error_count) === 0 &&
    typeof accuracy === "number" && Number.isFinite(accuracy) &&
    typeof interruption === "number" && Number.isFinite(interruption) &&
    typeof missedHelp === "number" && Number.isFinite(missedHelp) &&
    accuracy >= Number(criteria.accuracy_min) &&
    interruption <= Number(criteria.unnecessary_interruption_rate_max) &&
    missedHelp <= Number(criteria.missed_help_rate_max)
  );
}

function appendCells(row, values) {
  values.forEach((value) => row.append(makeElement("td", "", value)));
}

function showEvaluationState(title, detail, stateName) {
  elements.evaluationState.replaceChildren(
    makeElement("strong", "", title),
    makeElement("p", "", detail),
  );
  elements.evaluationState.hidden = false;
  elements.evaluationContent.hidden = true;
  elements.evaluationStatus.textContent = title;
  elements.evaluationStatus.dataset.state = stateName;
}

function renderEvaluation(summary) {
  const closure = summary?.artifact_version === "lurker-m5-closure-v1";
  if (
    (!closure && summary?.artifact_version !== "lurker-m5-v1") ||
    summary.publication_status !== "published" ||
    summary.split !== "heldout"
  ) {
    throw new Error("Published evaluation has an unsupported schema");
  }
  const primaryKey = String(summary.primary_context_k);
  const primary = summary.context_metrics?.[primaryKey];
  if (!primary) throw new Error("Published evaluation is missing its primary context");

  const passed = !closure && metricPasses(primary, summary.criteria);
  elements.evaluationStatus.textContent = closure ? "Published NO-GO" : "Published";
  elements.evaluationStatus.dataset.state = closure ? "fail" : "published";
  elements.evaluationPrimaryStatus.textContent = passed ? "PASS" : "FAIL";
  elements.evaluationPrimaryStatus.dataset.state = passed ? "pass" : "fail";
  elements.evaluationGenerated.textContent = `Published ${formatTime(summary.published_at || summary.generated_at)}`;
  elements.evaluationEnvironment.textContent = `${summary.device} · ${summary.hardware}`;
  elements.evaluationPolicy.textContent = `k=${primaryKey} · reply ${Number(summary.thresholds.reply_threshold).toFixed(2)} · react ${Number(summary.thresholds.react_threshold).toFixed(2)}`;

  const metricBindings = [
    [primary.accuracy, elements.evaluationAccuracy, elements.evaluationAccuracyCount],
    [primary.unnecessary_interruption_rate, elements.evaluationInterruption, elements.evaluationInterruptionCount],
    [primary.missed_help_rate, elements.evaluationMissedHelp, elements.evaluationMissedHelpCount],
  ];
  metricBindings.forEach(([metric, rateElement, countElement]) => {
    rateElement.textContent = evaluationRate(metric);
    countElement.textContent = evaluationCount(metric);
  });
  const reactRecallNote = closure && primary.react_recall?.denominator === 0
    ? " · REACT recall N/A (0 unanimous REACT cases)"
    : "";
  elements.evaluationSampleNote.textContent = `${primary.non_ambiguous_count} scored · ${primary.ambiguous_count} ambiguous · ${primary.error_count} errors${reactRecallNote}`;

  elements.evaluationContextBody.replaceChildren();
  ["0", "3", "5"].forEach((key) => {
    const metrics = summary.context_metrics[key];
    const row = document.createElement("tr");
    appendCells(row, [
      key === primaryKey ? `${key} · primary` : key,
      `${evaluationRate(metrics.accuracy)} · ${evaluationCount(metrics.accuracy)}`,
      `${evaluationRate(metrics.unnecessary_interruption_rate)} · ${evaluationCount(metrics.unnecessary_interruption_rate)}`,
      `${evaluationRate(metrics.missed_help_rate)} · ${evaluationCount(metrics.missed_help_rate)}`,
      `${formatLatency(metrics.latency_ms.p50)} / ${formatLatency(metrics.latency_ms.p95)}`,
    ]);
    elements.evaluationContextBody.append(row);
  });

  elements.evaluationBaselineBody.replaceChildren();
  const questionBaselineComplete = summary.baselines.always_reply_to_questions?.status === "COMPLETE_HELDOUT";
  const systems = [
    ["Strands Decider", { metrics: primary, model_calls: 0 }],
    [closure && !questionBaselineComplete ? "Question-mark rule (development reference)" : "Question-mark rule", summary.baselines.always_reply_to_questions],
    ["Bedrock judge", summary.baselines.bedrock_judge],
  ];
  systems.forEach(([name, baseline]) => {
    const row = document.createElement("tr");
    const metrics = baseline.metrics;
    if (!metrics) {
      appendCells(row, [name, String(baseline.model_calls), "Not run", "Not run", "Not run"]);
      elements.evaluationBaselineBody.append(row);
      return;
    }
    appendCells(row, [
      name,
      String(baseline.model_calls),
      `${evaluationRate(metrics.accuracy)} · ${evaluationCount(metrics.accuracy)}`,
      `${evaluationRate(metrics.unnecessary_interruption_rate)} · ${evaluationCount(metrics.unnecessary_interruption_rate)}`,
      `${evaluationRate(metrics.missed_help_rate)} · ${evaluationCount(metrics.missed_help_rate)}`,
    ]);
    elements.evaluationBaselineBody.append(row);
  });
  elements.evaluationBaselineNote.textContent = closure
    ? (questionBaselineComplete
      ? "The punctuation rule uses the same 15 held-out cases. The Bedrock judge was not run and requires separate approval."
      : "The punctuation rule uses the accessible 90-case development reference. The held-out Bedrock judge was not run and requires separate approval.")
    : "All systems use the same held-out cases.";

  elements.evaluationCalibrationBody.replaceChildren();
  primary.calibration.forEach((bucket) => {
    const row = document.createElement("tr");
    appendCells(row, [bucket.bin, evaluationCount(bucket), evaluationRate(bucket)]);
    elements.evaluationCalibrationBody.append(row);
  });

  elements.evaluationBoundaryText.textContent = closure
    ? (summary.acceptance?.implementation_completion === "TECHNICALLY_COMPLETE"
      ? "M5 is technically complete by owner approval, but model performance remains NO-GO: held-out accuracy was 66.7%, unnecessary interruption was 66.7%, and REACT recall is unavailable. This is not production readiness."
      : "Model performance is NO-GO: held-out accuracy was 66.7%, unnecessary interruption was 66.7%, and REACT recall is unavailable. Technical closure remains pending owner approval; this is not production readiness.")
    : "Ambiguous cases are listed in the saved report and excluded from scored rates. A passing result does not establish production readiness or statistical generalization.";

  elements.evaluationState.hidden = true;
  elements.evaluationContent.hidden = false;
}

async function loadEvaluation() {
  if (state.evaluationLoaded || state.evaluationLoading) return;
  state.evaluationLoading = true;
  showEvaluationState("Loading", "Checking for an explicitly published M5 result…", "loading");
  try {
    const summary = await loadJson("/api/eval/latest");
    renderEvaluation(summary);
    state.evaluationLoaded = true;
  } catch (error) {
    if (error.status === 404) {
      showEvaluationState(
        "Not published",
        "No final M5 result is published. No sample or provisional numbers are shown.",
        "empty",
      );
    } else {
      showEvaluationState(
        "Unavailable",
        "The published evaluation could not be validated or loaded. The saved report remains authoritative.",
        "error",
      );
    }
  } finally {
    state.evaluationLoading = false;
  }
}

async function hydrate() {
  const requests = await Promise.allSettled([
    loadJson("/health"),
    loadJson("/api/metrics"),
    loadJson("/api/decisions?limit=50"),
    loadJson("/api/about"),
  ]);

  const [healthResult, metricsResult, decisionsResult, aboutResult] = requests;
  if (healthResult.status === "fulfilled") {
    const health = healthResult.value;
    const mock = health.decider_mode === "mock";
    elements.modeChip.textContent = mock ? "Mock mode" : "Real mode";
    elements.mockBanner.hidden = !mock;
  } else {
    elements.modeChip.textContent = "Unavailable";
    showAlert("The service status could not be loaded.");
  }

  if (metricsResult.status === "fulfilled") renderCounters(metricsResult.value.counters);
  if (decisionsResult.status === "fulfilled") {
    state.decisions = mergeDecisions(decisionsResult.value);
    renderDecisionHero(state.decisions[0]);
    renderDecisionLog();
  }
  if (aboutResult.status === "fulfilled") renderAbout(aboutResult.value);
  connectSocket();
}

function activateTab(name) {
  const live = name === "live";
  const about = name === "about";
  const evaluation = name === "evaluation";
  elements.liveTab.classList.toggle("is-active", live);
  elements.liveTab.setAttribute("aria-selected", String(live));
  elements.aboutTab.classList.toggle("is-active", about);
  elements.aboutTab.setAttribute("aria-selected", String(about));
  elements.evaluationTab.classList.toggle("is-active", evaluation);
  elements.evaluationTab.setAttribute("aria-selected", String(evaluation));
  elements.livePanel.hidden = !live;
  elements.aboutPanel.hidden = !about;
  elements.evaluationPanel.hidden = !evaluation;
  if (evaluation) loadEvaluation();
}

elements.liveTab.addEventListener("click", () => activateTab("live"));
elements.aboutTab.addEventListener("click", () => activateTab("about"));
elements.evaluationTab.addEventListener("click", () => activateTab("evaluation"));

elements.sender.addEventListener("change", () => {
  elements.thirdName.hidden = elements.sender.value !== "__third__";
  if (!elements.thirdName.hidden) elements.thirdName.focus();
});

elements.thirdName.addEventListener("input", () => {
  const name = elements.thirdName.value.trim() || "Sam";
  elements.thirdOption.textContent = name;
});

elements.messageInput.addEventListener("input", () => {
  elements.messageInput.style.height = "auto";
  elements.messageInput.style.height = `${Math.min(elements.messageInput.scrollHeight, 120)}px`;
  updateComposerState();
});

elements.messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (!elements.sendButton.disabled) elements.form.requestSubmit();
  }
});

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  clearAlert();
  const text = elements.messageInput.value.trim();
  const sender = selectedSender();
  if (!text || !sender || !state.socket || state.socket.readyState !== WebSocket.OPEN) {
    showAlert("Connect to the service and enter a message before sending.");
    return;
  }
  state.pendingMessage = { sender, text };
  state.socket.send(JSON.stringify({ type: "message", sender, text }));
  updateComposerState();
  state.pendingTimer = window.setTimeout(() => {
    if (!state.pendingMessage) return;
    state.pendingMessage = null;
    showAlert("The message was sent, but no confirmation arrived. Check the connection before retrying.");
    updateComposerState();
  }, 8000);
});

elements.resetButton.addEventListener("click", async () => {
  const confirmed = window.confirm("Reset this demo session? Historical JSONL is rotated and preserved.");
  if (!confirmed) return;
  elements.resetButton.disabled = true;
  try {
    await loadJson("/api/reset", { method: "POST" });
    state.messages.clear();
    state.queuedReactions.clear();
    state.reactionKeys.clear();
    state.decisions = [];
    elements.messageList.replaceChildren();
    showEmptyChat();
    renderDecisionHero(null);
    renderDecisionLog();
    const metrics = await loadJson("/api/metrics");
    renderCounters(metrics.counters);
    clearAlert();
    announce("The live demo session was reset. Historical logs were preserved.");
  } catch (_error) {
    showAlert("The session could not be reset. Nothing was cleared in the browser.");
  } finally {
    updateComposerState();
  }
});

hydrate();
