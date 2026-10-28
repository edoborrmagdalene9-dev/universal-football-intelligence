/* Additive live fixture-feed bridge. Uses the existing Render API and keeps provider values as text. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const baseInput = $("esiApiBase");
  const dateInput = $("esiFeedDate");
  const output = $("esiFeedOutput");
  const status = $("esiFeedStatus");
  const connectButton = $("esiConnectFeed");
  const fixturesButton = $("esiLoadFixtures");
  const detailsButton = $("esiLoadFixtureDetails");
  const stopButton = $("esiStopFeed");
  const idInput = $("esiProviderFixtureId");
  if (!baseInput || !dateInput || !output || !status || !fixturesButton || !idInput) return;

  const DEFAULT_API = "https://universal-football-intelligence.onrender.com";
  let refreshTimer = null;
  let lastFixtures = [];

  if (!baseInput.value) baseInput.value = DEFAULT_API;
  if (!dateInput.value) {
    const now = new Date();
    dateInput.value = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
  }

  function apiBase() {
    const value = (baseInput.value || "").trim().replace(/\/+$/, "");
    if (!/^https:\/\//i.test(value)) throw new Error("Enter the HTTPS URL of the deployed UFI backend.");
    return value;
  }

  async function requestJson(path) {
    const response = await fetch(apiBase() + path, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store"
    });
    let payload;
    try { payload = await response.json(); }
    catch (_) { throw new Error("Backend returned a non-JSON response (HTTP " + response.status + ")."); }
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || ("Backend returned HTTP " + response.status + "."));
    }
    return payload;
  }

  function rowsFrom(payload) {
    let value = payload;
    for (let i = 0; i < 5 && value && typeof value === "object"; i++) {
      if (Array.isArray(value)) return value;
      if (Array.isArray(value.data)) return value.data;
      value = value.data;
    }
    return [];
  }

  function fixtureName(row) {
    if (row && typeof row.name === "string" && row.name.trim()) return row.name.trim();
    const participants = Array.isArray(row && row.participants) ? row.participants : [];
    let home = "", away = "";
    participants.forEach((participant) => {
      const side = String((participant && participant.meta && participant.meta.location) || "").toLowerCase();
      const name = String((participant && participant.name) || "").trim();
      if (side === "home") home = name;
      if (side === "away") away = name;
    });
    return home && away ? home + " vs " + away : "Fixture " + String((row && row.id) || "unknown");
  }

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = String(value);
    return node;
  }

  function renderFixtures(payload) {
    lastFixtures = rowsFrom(payload).filter((row) => row && row.id !== undefined && row.id !== null && /^\d+$/.test(String(row.id)));
    output.replaceChildren();
    if (!lastFixtures.length) {
      output.appendChild(element("p", "muted", "No fixtures returned for " + dateInput.value + ". Try another date or check provider coverage."));
      status.textContent = "Feed request succeeded, but the provider returned no usable fixtures for " + dateInput.value + ".";
      return;
    }
    const table = element("table", "fixture-feed-table");
    const head = element("thead");
    const headerRow = element("tr");
    ["Fixture", "Kickoff", "Provider ID", "Action"].forEach((label) => headerRow.appendChild(element("th", "", label)));
    head.appendChild(headerRow);
    table.appendChild(head);
    const body = element("tbody");
    lastFixtures.forEach((fixture) => {
      const row = element("tr");
      const kickoff = fixture.starting_at || fixture.kickoff || fixture.commence_time || "Unknown";
      const id = String(fixture.id);
      row.appendChild(element("td", "", fixtureName(fixture)));
      row.appendChild(element("td", "", kickoff));
      row.appendChild(element("td", "", id));
      const actionCell = element("td");
      const choose = element("button", "button", "Use this fixture");
      choose.type = "button";
      choose.dataset.fixtureId = id;
      choose.addEventListener("click", () => {
        idInput.value = id;
        status.textContent = "Selected " + fixtureName(fixture) + " (provider fixture " + id + "). Choose the matching historical league code, then run the connected pipeline.";
        const details = $("esiFixtureDetailsOutput");
        if (details) details.textContent = "Fixture selected. Load selected fixture details to inspect the provider record.";
      });
      actionCell.appendChild(choose);
      row.appendChild(actionCell);
      body.appendChild(row);
    });
    table.appendChild(body);
    output.appendChild(table);
    status.textContent = "Loaded " + lastFixtures.length + " source fixture(s) from " + String(payload.source || "the configured provider") + " for " + dateInput.value + ". Select a fixture to send its ID to the prediction pipeline.";
  }

  async function loadFixtures() {
    const day = dateInput.value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new Error("Choose a valid fixture date.");
    status.textContent = "Loading source fixtures for " + day + "…";
    const payload = await requestJson("/api/fixtures?date=" + encodeURIComponent(day));
    renderFixtures(payload);
    return payload;
  }

  async function connectAndLoad() {
    if (connectButton) connectButton.disabled = true;
    if (fixturesButton) fixturesButton.disabled = true;
    try {
      status.textContent = "Checking backend health…";
      const health = await requestJson("/api/health");
      if (health.ok !== true) throw new Error("Backend health check did not return ok=true.");
      await loadFixtures();
      if (refreshTimer) clearInterval(refreshTimer);
      // Refresh conservatively to avoid hammering a provider quota.
      refreshTimer = setInterval(() => {
        loadFixtures().catch((error) => { status.textContent = "Auto-refresh paused after an error: " + error.message; });
      }, 300000);
    } catch (error) {
      status.textContent = "Feed connection failed: " + String(error && error.message || error);
    } finally {
      if (connectButton) connectButton.disabled = false;
      if (fixturesButton) fixturesButton.disabled = false;
    }
  }

  function detailsOutput() {
    let node = $("esiFixtureDetailsOutput");
    if (!node) {
      node = element("pre", "code-output");
      node.id = "esiFixtureDetailsOutput";
      node.setAttribute("aria-live", "polite");
      output.insertAdjacentElement("afterend", node);
    }
    return node;
  }

  if (connectButton) connectButton.addEventListener("click", connectAndLoad);
  fixturesButton.addEventListener("click", async () => {
    fixturesButton.disabled = true;
    try { await loadFixtures(); }
    catch (error) { status.textContent = "Fixture request failed: " + String(error && error.message || error); }
    finally { fixturesButton.disabled = false; }
  });

  if (detailsButton) detailsButton.addEventListener("click", async () => {
    const id = (idInput.value || "").trim();
    if (!/^\d+$/.test(id)) {
      status.textContent = "Select a fixture from the loaded list or enter its numeric provider ID first.";
      return;
    }
    detailsButton.disabled = true;
    try {
      status.textContent = "Loading provider details for fixture " + id + "…";
      const payload = await requestJson("/api/fixture?id=" + encodeURIComponent(id));
      detailsOutput().textContent = JSON.stringify(payload, null, 2);
      status.textContent = "Provider details loaded for fixture " + id + ". Missing events, statistics or scores remain unknown if the source did not provide them.";
    } catch (error) {
      status.textContent = "Fixture details failed: " + String(error && error.message || error);
    } finally { detailsButton.disabled = false; }
  });

  if (stopButton) stopButton.addEventListener("click", () => {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = null;
    status.textContent = "Auto-refresh stopped. Use Load fixtures by date or Connect / refresh live feed when ready.";
  });

  // Expose a read-only test seam; production UI behavior still runs through user controls.
  window.UfiLiveFixtureFeed = Object.freeze({
    getLastFixtureCount: () => lastFixtures.length,
    getApiBase: () => apiBase()
  });
})();
