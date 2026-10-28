/* Additive UI bridge for the source-fixture -> historical-model pipeline. */
(function () {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const button = byId("ufiRunEndToEndPipeline");
  if (!button) return;

  const baseInput = byId("esiApiBase");
  if (baseInput && !baseInput.value) {
    baseInput.value = "https://universal-football-intelligence.onrender.com";
  }

  button.addEventListener("click", async function () {
    const status = byId("ufiPipelineStatus");
    const output = byId("ufiPipelineOutput");
    const fixtureId = (byId("esiProviderFixtureId")?.value || "").trim();
    const league = (byId("ufiPipelineLeague")?.value || "").trim();
    const seasons = (byId("ufiPipelineSeasons")?.value || "3").trim();
    const base = (baseInput?.value || "").trim().replace(/\/+$/, "");

    if (!base || !/^https:\/\//i.test(base)) {
      status.textContent = "Enter the HTTPS URL of the deployed UFI backend.";
      return;
    }
    if (!/^\d+$/.test(fixtureId)) {
      status.textContent = "Enter a numeric provider fixture ID from the loaded fixture feed.";
      return;
    }
    if (!league) {
      status.textContent = "Choose the historical league code that matches this fixture competition. The app will not guess a mapping.";
      return;
    }
    if (!/^[1-8]$/.test(seasons)) {
      status.textContent = "Season window must be an integer from 1 to 8.";
      return;
    }

    button.disabled = true;
    button.textContent = "Running connected pipeline…";
    status.textContent = "Fetching the source fixture and passing its teams into the historical score model. Market approval remains separate.";
    output.textContent = "Working…";
    try {
      const params = new URLSearchParams({ fixture_id: fixtureId, league, seasons });
      const response = await fetch(base + "/api/pipeline/predict?" + params.toString(), {
        method: "GET",
        headers: { "Accept": "application/json" },
        cache: "no-store"
      });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || ("Backend returned HTTP " + response.status));
      }
      const fixture = payload.fixture_source || {};
      const model = payload.historical_model || {};
      const models = model.models || (model.model && model.model.models) || {};
      const topScores = {};
      Object.keys(models).forEach(function (name) {
        topScores[name] = (models[name].top_scores || []).slice(0, 5).map(function (row) {
          return {
            score: String(row.home) + "-" + String(row.away),
            probability: row.p,
            fair_odds: row.fair_odds
          };
        });
      });
      const view = {
        pipeline_status: payload.pipeline_status,
        fixture: fixture,
        stages: payload.stages,
        context_availability: payload.match_context,
        historical_model_status: model.status || model.model?.status || "NEEDS_DATA",
        top_scorelines: topScores,
        market_gate: payload.market_gate || "WAIT",
        gate_reasons: payload.gate_reasons || [],
        warning: payload.warning || "Experimental model output; not a guaranteed result or betting signal."
      };
      output.textContent = JSON.stringify(view, null, 2);
      status.textContent = payload.pipeline_status === "model_ready_market_wait"
        ? "Fixture ingestion and historical model ran. Market gate remains WAIT; tactical/player joins and exact-score market validation are not cleared."
        : "Fixture loaded, but the historical model needs more usable data. No scoreline was fabricated; market gate remains WAIT.";
      if (window.posthog && typeof window.posthog.capture === "function") {
        window.posthog.capture("ufi_pipeline_run", {
          pipeline_status: payload.pipeline_status,
          model_status: view.historical_model_status,
          market_gate: view.market_gate
        });
      }
    } catch (error) {
      status.textContent = "Pipeline did not complete: " + String(error && error.message || error);
      output.textContent = "No integrated prediction was produced. Check backend reachability, fixture ID, league code and historical coverage.";
    } finally {
      button.disabled = false;
      button.textContent = "Run connected fixture → model pipeline";
    }
  });
})();
