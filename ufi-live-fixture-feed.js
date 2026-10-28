/* Additive, isolated fixture picker for the connected score-model pipeline.
   Existing live-feed controls remain owned by exact-score-intelligence.js. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const button = $("ufiPipelineLoadFixtures");
  const picker = $("ufiPipelineFixturePicker");
  const baseInput = $("esiApiBase");
  const dateInput = $("esiFeedDate");
  const idInput = $("esiProviderFixtureId");
  if (!button || !picker || !idInput) return;

  const DEFAULT_API = "https://universal-football-intelligence.onrender.com";
  if (baseInput && !baseInput.value) baseInput.value = DEFAULT_API;
  if (dateInput && !dateInput.value) {
    const now = new Date();
    dateInput.value = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
  }

  function apiBase() {
    const value = String((baseInput && baseInput.value) || DEFAULT_API).trim().replace(/\/+$/, "");
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
    if (!response.ok || payload.ok === false) throw new Error(payload.error || ("Backend returned HTTP " + response.status + "."));
    return payload;
  }

  function rowsFrom(payload) {
    let value = payload;
    for (let i = 0; i < 6 && value && typeof value === "object"; i++) {
      if (Array.isArray(value)) return value;
      if (Array.isArray(value.data)) return value.data;
      value = value.data;
    }
    return [];
  }

  function fixtureName(fixture) {
    if (typeof fixture.name === "string" && fixture.name.trim()) return fixture.name.trim();
    let home = "", away = "";
    (Array.isArray(fixture.participants) ? fixture.participants : []).forEach((p) => {
      const side = String((p && p.meta && p.meta.location) || "").toLowerCase();
      if (side === "home") home = String(p.name || "").trim();
      if (side === "away") away = String(p.name || "").trim();
    });
    return home && away ? home + " vs " + away : "Fixture " + String(fixture.id);
  }

  function make(tag, text) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function render(payload) {
    const fixtures = rowsFrom(payload).filter((f) => f && f.id !== undefined && /^\d+$/.test(String(f.id)));
    picker.replaceChildren();
    if (!fixtures.length) {
      picker.textContent = "No usable source fixtures returned for " + (dateInput && dateInput.value || "the selected date") + ". Check provider coverage or try another date.";
      return;
    }
    const intro = make("p", "Loaded " + fixtures.length + " source fixture(s) from " + String(payload.source || "the configured provider") + ". Select one to populate the provider ID for the model pipeline.");
    picker.appendChild(intro);
    const list = make("div");
    list.className = "button-row";
    fixtures.forEach((fixture) => {
      const id = String(fixture.id);
      const name = fixtureName(fixture);
      const kickoff = fixture.starting_at || fixture.kickoff || fixture.commence_time || "Kickoff unknown";
      const choose = make("button", name + " · " + kickoff + " · ID " + id);
      choose.type = "button";
      choose.className = "button";
      choose.dataset.ufiPipelineFixtureId = id;
      choose.addEventListener("click", () => {
        idInput.value = id;
        const participants = Array.isArray(fixture.participants) ? fixture.participants : [];
        participants.forEach((p) => {
          const side = String((p && p.meta && p.meta.location) || "").toLowerCase();
          const team = String((p && p.name) || "").trim();
          if (side === "home" && $("esiHome")) $("esiHome").value = team;
          if (side === "away" && $("esiAway")) $("esiAway").value = team;
        });
        picker.querySelectorAll("[data-ufi-pipeline-fixture-id]").forEach((el) => { el.setAttribute("aria-pressed", String(el === choose)); });
        const pipelineStatus = $("ufiPipelineStatus");
        if (pipelineStatus) pipelineStatus.textContent = "Selected " + name + " (provider fixture " + id + "). Choose the matching historical league code, then run the connected pipeline.";
      });
      choose.setAttribute("aria-pressed", "false");
      list.appendChild(choose);
    });
    picker.appendChild(list);
  }

  button.addEventListener("click", async () => {
    const day = String((dateInput && dateInput.value) || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
      picker.textContent = "Choose a valid fixture date first.";
      return;
    }
    button.disabled = true;
    button.textContent = "Loading source fixtures…";
    picker.textContent = "Fetching fixtures for " + day + " from the configured UFI backend…";
    try {
      render(await requestJson("/api/fixtures?date=" + encodeURIComponent(day)));
    } catch (error) {
      picker.textContent = "Fixture request failed: " + String(error && error.message || error) + ". The existing live-feed controls are unchanged.";
    } finally {
      button.disabled = false;
      button.textContent = "Load source fixtures for prediction";
    }
  });
})();
