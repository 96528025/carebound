const state = {
  currentUser: "alice",
  bootstrap: null,
  proof: null,
};

const userSelect = document.querySelector("#userSelect");
const membersList = document.querySelector("#membersList");
const sharedList = document.querySelector("#sharedList");
const proofPanel = document.querySelector("#proofPanel");
const chatLog = document.querySelector("#chatLog");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const testResults = document.querySelector("#testResults");
const planResults = document.querySelector("#planResults");

function labelize(value) {
  return value.replaceAll("_", " ");
}

function scopeTags(scopes, kind) {
  if (!scopes || scopes.length === 0) return `<span class="scope">none</span>`;
  return scopes.map((scope) => `<span class="scope ${kind}">${scope}</span>`).join("");
}

function renderProof(proof) {
  state.proof = proof;
  const identity = proof.identity;
  proofPanel.innerHTML = `
    <div class="proof-row">
      <strong>Scalekit identity</strong>
      ${identity.name} (${identity.id})<br />
      ${identity.identity_mode}<br />
      AgentKit identifier: ${identity.scalekit_identifier}
    </div>
    <div class="proof-row">
      <strong>Scalekit AgentKit</strong>
      Connection: ${proof.scalekit_agentkit.connection_name}<br />
      Identifier: ${proof.scalekit_agentkit.identifier}<br />
      Status: ${proof.scalekit_agentkit.status || "not_checked"}<br />
      ${proof.scalekit_agentkit.connected_account_id ? `Connected account: ${proof.scalekit_agentkit.connected_account_id}<br />` : ""}
      ${proof.scalekit_agentkit.tool_name ? `Tool: ${proof.scalekit_agentkit.tool_name}<br />` : ""}
      ${proof.scalekit_agentkit.authorization_link ? `<a href="${proof.scalekit_agentkit.authorization_link}" target="_blank" rel="noreferrer">Open authorization link</a><br />` : ""}
      ${proof.scalekit_agentkit.tool_output_preview ? `Tool output: ${proof.scalekit_agentkit.tool_output_preview}<br />` : ""}
      ${proof.scalekit_agentkit.error ? proof.scalekit_agentkit.error : ""}
    </div>
    <div class="proof-row">
      <strong>Household / role</strong>
      ${identity.household_id} / ${identity.role}
    </div>
    <div class="proof-row">
      <strong>Allowed scopes</strong>
      <div class="scope-list">${scopeTags(proof.allowed_scopes, "allowed")}</div>
    </div>
    <div class="proof-row">
      <strong>Blocked scopes</strong>
      <div class="scope-list">${scopeTags(proof.blocked_scopes, "blocked")}</div>
    </div>
    <div class="proof-row">
      <strong>Last queried scopes</strong>
      <div class="scope-list">${scopeTags(proof.last_queried_scopes, "queried")}</div>
    </div>
    <div class="proof-row">
      <strong>Policy decision</strong>
      Intent: ${proof.policy.intent}<br />
      Enforcement: ${proof.policy.enforcement_point}<br />
      Unauthorized collections queried: ${proof.policy.unauthorized_collections_queried}<br />
      ${proof.policy.reason}
    </div>
    <div class="proof-row">
      <strong>Blocked before retrieval</strong>
      <div class="scope-list">${scopeTags(proof.policy.blocked_scopes_attempted, "blocked")}</div>
    </div>
    <div class="proof-row">
      <strong>Retrieval</strong>
      ${proof.retrieved_memory_count} memories retrieved<br />
      ${proof.blocked_access_attempts} blocked attempts
    </div>
    <div class="proof-row">
      <strong>Storage mode</strong>
      ${proof.storage_mode}
    </div>
  `;
}

function renderBootstrap(data) {
  state.bootstrap = data;
  userSelect.innerHTML = data.members
    .map((member) => `<option value="${member.id}">${member.name}</option>`)
    .join("");
  userSelect.value = state.currentUser;
  const shared = data.household.shared;
  sharedList.innerHTML = Object.entries(shared)
    .map(([key, value]) => `<div class="shared-item"><strong>${labelize(key)}</strong>${value}</div>`)
    .join("");
  renderMembers();
  renderProof(data.proof);
}

function renderMembers() {
  membersList.innerHTML = state.bootstrap.members
    .map((member) => {
      const active = member.id === state.currentUser ? "active" : "";
      const detail = `${member.relationship}, ${member.age} years old`;
      return `
        <div class="member-card ${active}">
          <strong>${member.name}</strong>
          ${detail}<br />
          <span class="role">${member.role}</span>
        </div>
      `;
    })
    .join("");
}

function addMessage(kind, text, note = "") {
  const div = document.createElement("div");
  div.className = `message ${kind}`;
  div.innerHTML = `${text}${note ? `<small>${note}</small>` : ""}`;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function loadBootstrap() {
  const res = await fetch(`/api/bootstrap?user_id=${state.currentUser}`);
  renderBootstrap(await res.json());
}

async function ask(message) {
  addMessage("user", message);
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: state.currentUser, message }),
  });
  const data = await res.json();
  renderProof(data.proof);
  const queried = data.proof.last_queried_scopes.join(", ") || "none";
  const blocked = data.proof.policy.blocked_scopes_attempted.join(", ") || "none";
  addMessage("agent", data.answer, `intent: ${data.proof.policy.intent} / queried: ${queried} / blocked before retrieval: ${blocked}`);
}

async function importCareEmail(targetScope = null, useScalekit = false) {
  const res = await fetch("/api/import-care-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: state.currentUser, target_scope: targetScope, use_scalekit: useScalekit }),
  });
  const data = await res.json();
  renderProof(data.proof);
  const note = data.authorization_link ? "Scalekit returned an authorization link." : "Import is scoped to the current Scalekit identifier.";
  addMessage("agent", data.message, note);
}

async function runTests() {
  testResults.innerHTML = "";
  const res = await fetch("/api/run-tests", { method: "POST" });
  const data = await res.json();
  testResults.innerHTML = data.results
    .map((result, index) => `
      <div class="test-card">
        <div><span class="${result.passed ? "pass" : "fail"}">${result.passed ? "PASS" : "FAIL"}</span> Test ${index + 1}: ${result.user_id} asks "${result.message}"</div>
        <div>Intent: ${result.policy_intent}</div>
        <div>Expected queried: ${result.expected_queried.join(", ") || "none"}</div>
        <div>Expected blocked: ${result.expected_blocked.join(", ") || "none"}</div>
        <div>Actual queried: ${result.queried_scopes.join(", ") || "none"}</div>
        <div>Blocked before retrieval: ${result.blocked_scopes_attempted.join(", ") || "none"}</div>
      </div>
    `)
    .join("");
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function renderPlan(data) {
  if (!data.ok) {
    const link = data.authorization_link
      ? ` <a href="${data.authorization_link}" target="_blank" rel="noreferrer">Open authorization link</a>`
      : "";
    planResults.innerHTML = `<div class="test-card"><div>${escapeHtml(data.message)}${link}</div></div>`;
    return;
  }
  if (data.proof) renderProof(data.proof);
  if (!data.appointments.length) {
    planResults.innerHTML = `<div class="test-card"><div>No appointment found in the email for this identity.</div></div>`;
    return;
  }
  planResults.innerHTML = data.appointments
    .map((appt) => {
      const maps = appt.maps_url
        ? `<a href="${appt.maps_url}" target="_blank" rel="noreferrer">Open Google Maps route</a>`
        : "no location found";
      const cal = appt.calendar
        ? `Calendar: ${escapeHtml(appt.calendar.status)} (${escapeHtml(appt.calendar.mode)})${
            appt.calendar.authorization_link
              ? ` &middot; <a href="${appt.calendar.authorization_link}" target="_blank" rel="noreferrer">Authorize Calendar</a>`
              : ""
          }`
        : "Calendar: not added (use Plan + add to Calendar)";
      return `
        <div class="test-card">
          <div><strong>${escapeHtml(appt.title)}</strong></div>
          <div>When: ${escapeHtml(appt.start) || "n/a"} &ndash; ${escapeHtml(appt.end) || "n/a"}</div>
          <div>Where: ${escapeHtml(appt.location) || "n/a"}</div>
          <div>Route: ${maps}</div>
          <div>${cal}</div>
          <div><small>extracted by: ${escapeHtml(appt.source)}</small></div>
        </div>
      `;
    })
    .join("");
}

async function planAppointments(createEvents = false) {
  planResults.innerHTML = `<div class="test-card"><div>Reading email and planning route...</div></div>`;
  const res = await fetch("/api/plan-appointments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: state.currentUser, use_scalekit: false, create_events: createEvents }),
  });
  const data = await res.json();
  renderPlan(data);
  addMessage("agent", data.message || "Appointment planning done.", "Email -> location/time -> Google Maps route -> Google Calendar.");
}

userSelect.addEventListener("change", async (event) => {
  state.currentUser = event.target.value;
  renderMembers();
  await loadBootstrap();
  addMessage("agent", `Identity switched to ${userSelect.options[userSelect.selectedIndex].text}.`, "Demo identity mode keeps the proof reliable.");
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;
  messageInput.value = "";
  await ask(message);
});

document.querySelectorAll(".quick-actions button[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => ask(button.dataset.prompt));
});

document.querySelector("#runTestsBtn").addEventListener("click", runTests);
document.querySelector("#importBtn").addEventListener("click", () => importCareEmail());
document.querySelector("#scalekitImportBtn").addEventListener("click", () => importCareEmail(null, true));
document.querySelector("#importEvaBtn").addEventListener("click", () => importCareEmail("member_eva_medical"));
document.querySelector("#planBtn").addEventListener("click", () => planAppointments(false));
document.querySelector("#planCalendarBtn").addEventListener("click", () => planAppointments(true));

loadBootstrap().then(() => {
  addMessage(
    "agent",
    "CareBound is ready. Try Chris asking about Eva, or Alice asking about Eva.",
    "The proof panel will show which VectorAI scopes were queried."
  );
});
