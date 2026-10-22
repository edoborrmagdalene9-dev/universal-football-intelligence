"""Local UFI research dashboard. Run: streamlit run dfs_optimizer/app.py"""
import io, json
import streamlit as st
import pandas as pd
import numpy as np
from src.pipeline import load_matches_csv, chronological_backtest, validate_contest_entries_csv
from src.event_simulator import simulate_event_points
from src.continuous_time_states import simulate_score_path
from src.player_data import read_player_stats_csv, build_player_projections, merge_projections_with_slate
from src.lineup_gate import validate_confirmed_lineup
from src.scoring_engine import expected_points, penalty_matchup_ev
from src.optimizer.pulp_optimizer import optimize_lineup, optimize_portfolio
from src.portfolio_simulation import evaluate_portfolio
from src.fantasyfi_monte_carlo import run_fantasyfi_monte_carlo
from src.microbehavioral_engine import fingerprint_player_roles, apply_tactical_multipliers, step_boundary_report
from src.fantasyfi_portfolio_optimizer import optimize_fantasyfi_portfolio

st.set_page_config(page_title="Universal Football Intelligence", page_icon="⚽", layout="wide")
st.title("⚽ Universal Football Intelligence")
st.caption("Local-first football research dashboard · validate before predicting")
st.warning("Research software only. No guaranteed winnings. Demo assumptions are synthetic; do not confuse them with real fixtures.")
page = st.sidebar.radio("Workspace", ["Overview", "Match data & backtest", "Contest ownership", "Event simulation", "Game-state lab", "Data standards"])
extension_page = st.sidebar.selectbox("Add-on workspace", ["Existing UFI pages", "FantasyFi optimizer", "Microbehavioral & Monte Carlo lab", "God-Mode DFS Research Lab", "Data Sources & Calibration Lab"])
if extension_page == "FantasyFi optimizer":
    page = "FantasyFi optimizer"
elif extension_page == "Microbehavioral & Monte Carlo lab":
    page = "Microbehavioral & Monte Carlo lab"
elif extension_page == "God-Mode DFS Research Lab":
    page = "God-Mode DFS Research Lab"
elif extension_page == "Data Sources & Calibration Lab":
    page = "Data Sources & Calibration Lab"
if page == "Overview":
    st.header("Research control centre")
    st.markdown("Validate licensed match data, run chronological baselines, inspect contest ownership, simulate player events and explore score-state scenarios.")
    cols=st.columns(4)
    for col,label,value in zip(cols,["Data validation","Chronological tests","Ownership analysis","Scenario simulation"],["01","02","03","04"]): col.metric(label,value)
    st.subheader("Recommended sequence")
    st.markdown("1. Validate historical results. 2. Review rejected rows and duplicates. 3. Run chronological backtests. 4. Compare held-out results with stronger baselines. 5. Only then experiment with ownership and payout assumptions.")
    st.info("No external data is downloaded automatically. Use the Data standards page for data sources and attribution.")
elif page == "Match data & backtest":
    st.header("Historical match data")
    st.write("Required CSV columns: date, home_team, away_team, home_goals, away_goals.")
    uploaded=st.file_uploader("Upload historical results CSV",type=["csv"],key="matches")
    min_train=st.number_input("Minimum initial training matches",min_value=10,max_value=5000,value=30,step=5)
    max_goals=st.slider("Score-grid maximum goals per team",5,15,8)
    if uploaded:
        try:
            result=load_matches_csv(io.StringIO(uploaded.getvalue().decode("utf-8-sig")))
            a,b,c=st.columns(3); a.metric("Valid matches",result["rows_valid"]); b.metric("Rejected",result["rows_rejected"]); c.metric("Received",result["rows_received"])
            if result["issues"]: st.dataframe(pd.DataFrame(result["issues"]),use_container_width=True)
            if result["matches"]:
                st.dataframe(pd.DataFrame(result["matches"]).head(20),use_container_width=True)
                if st.button("Run chronological train / validation / test backtest",type="primary"):
                    try:
                        report=chronological_backtest(result["matches"],min_train=int(min_train),max_goals=int(max_goals))
                        st.subheader("Held-out test metrics"); tm=report["test_metrics"]; cols=st.columns(3)
                        cols[0].metric("Test matches",tm["matches"])
                        cols[1].metric("Exact scoreline hit rate",f'{tm.get("exact_scoreline_accuracy",0):.1%}')
                        cols[2].metric("Result accuracy",f'{tm.get("result_accuracy",0):.1%}')
                        st.write("Multiclass Brier score (lower is better):",tm.get("mean_brier_score"))
                        st.json({k:v for k,v in report.items() if k!="predictions"})
                        pred=pd.DataFrame(report["predictions"]); st.dataframe(pred,use_container_width=True)
                        st.download_button("Download predictions CSV",pred.to_csv(index=False).encode(),"ufi_backtest_predictions.csv","text/csv")
                    except Exception as e: st.error(str(e))
        except Exception as e: st.error(f"Dataset validation failed: {e}")
elif page == "Contest ownership":
    st.header("Historical contest-entry ownership")
    st.write("CSV columns: entry_id, players. Player IDs are separated by |. Upload only data you are permitted to use; do not include personal data.")
    uploaded=st.file_uploader("Upload contest entries CSV",type=["csv"],key="entries")
    if uploaded:
        try:
            result=validate_contest_entries_csv(io.StringIO(uploaded.getvalue().decode("utf-8-sig")))
            a,b=st.columns(2); a.metric("Valid entries",result["entry_count"]); b.metric("Observed player IDs",len(result["player_ownership"]))
            st.dataframe(pd.DataFrame([{"player_id":p,"ownership":v} for p,v in sorted(result["player_ownership"].items(),key=lambda x:-x[1])]),use_container_width=True)
            if result["issues"]: st.dataframe(pd.DataFrame(result["issues"]))
            st.download_button("Download ownership summary JSON",json.dumps({k:v for k,v in result.items() if k!="entries"},indent=2).encode(),"ufi_ownership_summary.json","application/json")
            st.caption(result["warning"])
        except Exception as e: st.error(str(e))
elif page == "Event simulation":
    st.header("Player event simulation")
    st.write("Illustrative event rates and scoring assumptions—not forecasts.")
    with st.form("sim"):
        player=st.text_input("Player ID","demo_player")
        shots=st.number_input("Expected shots per match",0.0,20.0,2.0,0.25)
        key_passes=st.number_input("Expected key passes per match",0.0,20.0,1.0,0.25)
        shot_points=st.number_input("Points per shot",0.0,20.0,1.0,0.5)
        kp_points=st.number_input("Points per key pass",0.0,20.0,2.0,0.5)
        sims=st.select_slider("Simulations",[1000,5000,10000,25000,50000],value=10000)
        seed=st.number_input("Random seed",0,10000000,42)
        go=st.form_submit_button("Simulate")
    if go:
        result=simulate_event_points({player:{"shots":shots,"key_passes":key_passes,"points":{"shots":shot_points,"key_passes":kp_points}},},n_sims=int(sims),seed=int(seed))
        st.json(result["summary"][player]); st.caption("Calibrate event rates and scoring from historical data before relying on quantiles.")
elif page == "Game-state lab":
    st.header("Continuous-time score-state lab")
    with st.form("states"):
        hr=st.number_input("Home expected goals per match",0.0,8.0,1.5,0.1)
        ar=st.number_input("Away expected goals per match",0.0,8.0,1.1,0.1)
        lead=st.slider("Goal-rate multiplier while leading",0.1,3.0,0.9,0.1)
        trail=st.slider("Goal-rate multiplier while trailing",0.1,3.0,1.2,0.1)
        seed=st.number_input("Simulation seed",0,10000000,7)
        go=st.form_submit_button("Simulate one match")
    if go:
        result=simulate_score_path(hr,ar,home_state_multipliers={"lead":lead,"trail":trail},away_state_multipliers={"lead":lead,"trail":trail},seed=int(seed))
        st.metric("Final score",f'{result["home_goals"]} - {result["away_goals"]}')
        st.dataframe(pd.DataFrame(result["timeline"]),use_container_width=True)
        st.caption("Illustrative state multipliers, not fitted. Goal rates are assumed per 90-minute match.")

elif page == "FantasyFi optimizer":
    st.header("FantasyFi player-data and lineup optimizer")
    st.markdown("Use historical player-match statistics to build transparent empirical profiles, optionally verify an official lineup snapshot, then optimize a roster. Inputs remain local to this dashboard session.")
    st.warning("A live lineup provider is not configured. Upload a confirmed lineup from an official source; the gate rejects stale, malformed or out-of-window data rather than guessing.")
    with st.expander("FantasyFi rulebook edge calculator", expanded=False):
        st.caption("Use this to sanity-check the zero-tackle / high-interception asymmetry and the five-pass step function.")
        c1,c2,c3 = st.columns(3)
        completed_passes = c1.number_input("Completed passes", min_value=0, max_value=200, value=90, step=1)
        interceptions_90 = c2.number_input("Interceptions per 90", min_value=0.0, max_value=15.0, value=3.0, step=0.5)
        yellow_rate = c3.number_input("Expected yellow cards", min_value=0.0, max_value=2.0, value=0.2, step=0.1)
        d1,d2,d3 = st.columns(3)
        conversion = d1.number_input("Baseline penalty conversion", min_value=0.0, max_value=1.0, value=0.70, step=0.05)
        keeper_save = d2.number_input("Opponent GK penalty-save rate", min_value=0.0, max_value=1.0, value=0.25, step=0.05)
        penalty_position = d3.selectbox("Penalty taker position", ["forward","midfielder","defender","goalkeeper"])
        e1,e2 = st.columns(2)
        e1.metric("Actual pass points", int(completed_passes)//5)
        e2.metric("Expected interception points/90", f"{interceptions_90*4:.1f}")
        st.metric("Net interception minus expected yellow-card penalty", f"{interceptions_90*4-yellow_rate*4:.1f} points", help="Tackles contribute exactly zero points. Red cards and other events are not included in this small calculator.")
        matchup = penalty_matchup_ev(float(conversion), float(keeper_save), penalty_position)
        p1,p2,p3 = st.columns(3)
        p1.metric("Matchup-adjusted conversion", f'{matchup["effective_conversion_probability"]:.1%}')
        p2.metric("Taker penalty-event EV", f'{matchup["taker_expected_points"]:.2f}')
        p3.metric("Keeper penalty-save EV", f'{matchup["goalkeeper_expected_penalty_save_points"]:.2f}')
        st.caption("Penalty matchup adjustment treats the keeper save rate as incremental to the baseline conversion rate. Avoid double-counting if the taker rate is already opponent-adjusted.")
    with st.expander("Required input formats", expanded=False):
        st.markdown("**Historical player stats:** use `dfs_optimizer/datasets/player_stats_template.csv`, one row per player per match. Include zero-minute squad rows whenever possible. **Current slate:** use `dfs_optimizer/datasets/slate_template.csv` with player_id, team, position and salary. Optional projection/ownership columns may be provided. **Confirmed lineup:** use `dfs_optimizer/datasets/confirmed_lineups_template.csv`; timestamps must include a timezone, and each team must have exactly 11 starters marked true.")
    hist_file = st.file_uploader("1. Upload historical player-match stats CSV", type=["csv"], key="fantasyfi_history")
    slate_file = st.file_uploader("2. Upload current contest slate CSV", type=["csv"], key="fantasyfi_slate")
    lineup_file = st.file_uploader("3. Optional official confirmed lineup CSV", type=["csv"], key="fantasyfi_lineup")
    require_confirmed = st.checkbox("Require a fresh confirmed lineup before optimizing", value=True)
    recent_n = st.slider("Recent player-match rows used per player", 3, 30, 10)
    parsed_history = None
    profiles = []
    if hist_file:
        try:
            parsed_history = read_player_stats_csv(io.StringIO(hist_file.getvalue().decode("utf-8-sig")))
            a,b,c = st.columns(3)
            a.metric("Valid player-match rows", parsed_history["rows_valid"])
            b.metric("Rejected rows", parsed_history["rows_rejected"])
            c.metric("Players", len(set(r["player_id"] for r in parsed_history["rows"])))
            if parsed_history["issues"]:
                st.dataframe(pd.DataFrame(parsed_history["issues"]), use_container_width=True)
            profile_result = build_player_projections(parsed_history["rows"], recent_matches=int(recent_n))
            profiles = profile_result["profiles"]
            st.caption(profile_result["warning"])
            if profiles:
                display_profiles = [{k:v for k,v in p.items() if k not in {"projection_inputs","pass_count_pmf"}} for p in profiles]
                st.subheader("Historical player feature profiles")
                st.dataframe(pd.DataFrame(display_profiles), use_container_width=True)
                st.download_button("Download player feature profiles CSV", pd.DataFrame(display_profiles).to_csv(index=False).encode(), "ufi_player_feature_profiles.csv", "text/csv")
        except Exception as exc:
            st.error(f"Historical player data rejected: {exc}")
            parsed_history = None
    lineup_result = None
    if lineup_file:
        try:
            lineup_rows = list(__import__("csv").DictReader(io.StringIO(lineup_file.getvalue().decode("utf-8-sig"))))
            lineup_result = validate_confirmed_lineup(lineup_rows)
            if lineup_result["ready"]:
                st.success(f"Confirmed lineup gate passed for fixture {lineup_result['fixture_id']}; kickoff {lineup_result['kickoff_utc']}.")
                st.caption(f"Latest confirmation age: {lineup_result['confirmation_age_minutes']} minutes.")
            else:
                st.error("Confirmed lineup gate blocked export.")
                for issue in lineup_result["errors"]:
                    st.write("• " + issue)
        except Exception as exc:
            st.error(f"Could not validate lineup file: {exc}")
    if hist_file and slate_file and parsed_history and profiles:
        try:
            slate_rows = list(__import__("csv").DictReader(io.StringIO(slate_file.getvalue().decode("utf-8-sig"))))
            needed = {"player_id","team","position","salary"}
            if not slate_rows or not needed.issubset(set(slate_rows[0])):
                raise ValueError("Slate CSV must contain player_id, team, position and salary.")
            joined = merge_projections_with_slate(profiles, slate_rows, expected_points)
            if require_confirmed:
                if not lineup_result or not lineup_result.get("ready"):
                    st.info("Optimization is locked until a fresh official lineup CSV passes the confirmation gate.")
                    joined = []
                else:
                    confirmed_ids = {str(r["player_id"]) for r in lineup_result["rows"]}
                    joined = [r for r in joined if str(r["id"]) in confirmed_ids]
            if joined:
                st.subheader("Optimizer configuration")
                ca,cb,cc = st.columns(3)
                roster_size = int(ca.number_input("Roster size", min_value=1, max_value=30, value=9))
                salary_cap = float(cb.number_input("Salary cap", min_value=1.0, value=100.0, step=5.0))
                team_cap = int(cc.number_input("Maximum players per team (0 = off)", min_value=0, max_value=30, value=4))
                positions_json = st.text_input("Exact positional slots JSON", '{"GK":1,"DEF":3,"MID":3,"FWD":2}')
                if st.button("Optimize best single lineup", type="primary"):
                    try:
                        slots = json.loads(positions_json)
                        result = optimize_lineup(joined, roster_size, salary_cap, slots, team_cap=team_cap if team_cap else None)
                        lookup = {str(p["id"]):p for p in joined}
                        selected = [lookup[i] for i in result["players"]]
                        st.metric("Projected FantasyFi points", f'{result["projected_points"]:.2f}')
                        st.metric("Salary used", f'{result["salary"]:.2f} / {salary_cap:.2f}')
                        st.dataframe(pd.DataFrame(selected), use_container_width=True)
                        export = pd.DataFrame([{"entry_id":"lineup_1","player_id":p["id"],"team":p["team"],"position":p["position"],"salary":p["salary"],"projection":p["projection"]} for p in selected])
                        st.download_button("Download ready-to-review entry CSV", export.to_csv(index=False).encode(), "fantasyfi_entry.csv", "text/csv")
                    except Exception as exc:
                        st.error(f"Lineup optimization failed: {exc}")
                with st.expander("Multi-entry portfolio and Monte Carlo evaluation"):
                    count = int(st.number_input("Number of lineups", min_value=2, max_value=50, value=5))
                    distance = int(st.number_input("Minimum Hamming distance", min_value=1, max_value=18, value=2))
                    sims = int(st.select_slider("Monte Carlo simulations", [1000,5000,10000,25000], value=10000))
                    opponent_file = st.file_uploader("Optional opponent field CSV (entry_id,players; IDs separated by |)", type=["csv"], key="fantasyfi_opponents")
                    if st.button("Build portfolio and evaluate"):
                        try:
                            slots = json.loads(positions_json)
                            portfolio = optimize_portfolio(joined, count, roster_size, salary_cap, slots, min_hamming_distance=distance, team_cap=team_cap if team_cap else None)
                            st.dataframe(pd.DataFrame([{"entry_id":i+1,**r} for i,r in enumerate(portfolio)]), use_container_width=True)
                            opponent_lineups = []
                            if opponent_file:
                                opponent_rows = __import__("csv").DictReader(io.StringIO(opponent_file.getvalue().decode("utf-8-sig")))
                                for row in opponent_rows:
                                    opponent_lineups.append([p.strip() for p in row.get("players","").split("|") if p.strip()])
                            means = {str(p["id"]):float(p["projection"]) for p in joined}
                            profile_by_id = {str(p["player_id"]):p for p in profiles}
                            sds = {str(p["id"]):max(1.0,float(profile_by_id.get(str(p["id"]),{}).get("historical_points_sd",0))) for p in joined}
                            sim = evaluate_portfolio([r["players"] for r in portfolio], means, sds, opponent_lineups or None, simulations=sims)
                            st.subheader("Monte Carlo portfolio report")
                            st.json(sim)
                            st.caption("Without opponent entries, this reports score distributions only; it cannot estimate probability of winning the contest.")
                        except Exception as exc:
                            st.error(f"Portfolio evaluation failed: {exc}")
            elif not require_confirmed:
                st.warning("No current-slate players matched the historical player IDs.")
        except Exception as exc:
            st.error(f"Could not build projections or slate: {exc}")
    st.divider()
    st.markdown("**Operational workaround:** when no authorized live-lineup API is configured, obtain the official XI from the club/league/platform and upload it here. The gate only unlocks a fixture with a fresh confirmation timestamp inside the 45–75 minute pre-kickoff window. GitHub automation can test the code and run scheduled checks, but it cannot discover an official XI from thin air.")
    st.markdown("**Feature limits:** aerial win rate and set-piece shot rate are only as reliable as the uploaded provider stats. Empirical goal rate is not true xG; penalty conversion and goalkeeper penalty-save rates are Beta-smoothed and should be interpreted alongside sample counts.")


elif page == "Microbehavioral & Monte Carlo lab":
    st.header("FantasyFi micro-behavioral & Monte Carlo lab")
    st.caption("Add-on workspace: existing UFI and FantasyFi pages remain unchanged.")
    st.markdown("Upload player-match projections. The lab adds transparent role fingerprints, optional matchup multipliers, pass-step boundary diagnostics, a 10,000-run default event simulation and optional diversified lineup optimization.")
    st.info("Use real, permitted source data. Missing referee, weather, fatigue, tracking and ownership inputs are not invented; uncalibrated multipliers are scenario assumptions.")
    telemetry = st.file_uploader("Player projection CSV", type=["csv"], key="microbehavioral_projection_csv")
    sims = int(st.select_slider("Monte Carlo simulations", [1000, 5000, 10000, 25000], value=10000, key="micro_sims"))
    seed = int(st.number_input("Random seed (reproducibility)", min_value=0, max_value=2147483647, value=42, key="micro_seed"))
    if telemetry:
        try:
            raw = pd.read_csv(io.BytesIO(telemetry.getvalue()))
            st.subheader("Input preview")
            st.dataframe(raw.head(25), use_container_width=True)
            required = {"player_name", "position", "start_probability", "mean_passes", "mean_interceptions", "mean_shots_on_target", "mean_goals", "mean_assists", "clean_sheet_prob", "mean_yellow_cards", "mean_red_cards"}
            missing = sorted(required - set(raw.columns))
            if missing:
                st.error("Missing required Monte Carlo columns: " + ", ".join(missing))
            else:
                with st.expander("Optional tactical multipliers", expanded=False):
                    st.caption("Add optional columns such as pass_volume_multiplier, interception_multiplier, shot_on_target_multiplier, goal_multiplier, assist_multiplier, clean_sheet_multiplier and save_multiplier. Missing multipliers are neutral (1.0).")
                    use_multipliers = st.checkbox("Apply supplied multiplier columns", value=False)
                if st.button("Fingerprint players and run Monte Carlo", type="primary"):
                    try:
                        profiled = fingerprint_player_roles(raw)
                        adjusted = apply_tactical_multipliers(profiled) if use_multipliers else profiled
                        summary, score_matrix = run_fantasyfi_monte_carlo(adjusted, num_sims=sims, seed=seed)
                        st.subheader("Player behavioral fingerprints")
                        display_cols = [c for c in ["player_name", "position", "behavioral_fingerprint", "fingerprint_data_completeness"] if c in adjusted.columns]
                        st.dataframe(adjusted[display_cols], use_container_width=True)
                        st.subheader("Simulated point distributions")
                        st.dataframe(summary, use_container_width=True)
                        st.download_button("Download Monte Carlo summary CSV", summary.to_csv(index=False).encode(), "fantasyfi_monte_carlo_summary.csv", "text/csv")
                        st.session_state["ufi_micro_mc_matrix"] = score_matrix.tolist()
                        st.session_state["ufi_micro_mc_names"] = adjusted["player_name"].astype(str).tolist()
                        st.session_state["ufi_micro_mc_source"] = adjusted.to_dict(orient="records")
                        st.success(f"Completed {sims:,} simulations for {len(adjusted)} players.")
                    except Exception as exc:
                        st.error(f"Simulation failed: {exc}")
                if "projected_completed_passes" in raw.columns:
                    st.subheader("Pass step-function boundary report")
                    player_options = raw["player_name"].astype(str).tolist()
                    selected_pass_player = st.selectbox("Player to inspect", player_options, key="pass_boundary_player")
                    pass_row = raw.loc[raw["player_name"].astype(str) == selected_pass_player].iloc[0]
                    st.json(step_boundary_report(float(pass_row["projected_completed_passes"])))
                st.divider()
                st.subheader("Optional multi-entry lineup optimizer")
                st.caption("Requires salary and an official contest roster configuration. This optimizer uses MILP; it does not claim a quadratic MIQP solution.")
                if "salary" not in raw.columns:
                    st.warning("Add a salary column to the uploaded CSV to enable lineup optimization.")
                elif "ufi_micro_mc_matrix" not in st.session_state or st.session_state.get("ufi_micro_mc_names") != raw["player_name"].astype(str).tolist():
                    st.caption("Run the Monte Carlo simulation above first, then the optimizer can use its score matrix.")
                else:
                    budget = float(st.number_input("Salary cap", min_value=1.0, value=100.0, step=1.0, key="micro_budget"))
                    roster = int(st.number_input("Roster size", min_value=1, max_value=max(1, len(raw)), value=min(11, len(raw)), key="micro_roster"))
                    entries = int(st.number_input("Number of entries", min_value=1, max_value=20, value=3, key="micro_entries"))
                    max_overlap = int(st.number_input("Maximum players shared by any two entries", min_value=0, max_value=max(0, roster-1), value=min(8, max(0, roster-1)), key="micro_overlap"))
                    min_positions_json = st.text_input("Minimum players by position (JSON)", '{"GK":1,"DEF":3,"MID":3,"FWD":1}', key="micro_min_positions")
                    max_positions_json = st.text_input("Maximum players by position (JSON)", '{"GK":1,"DEF":5,"MID":5,"FWD":3}', key="micro_max_positions")
                    own_col = st.selectbox("Ownership column", ["None"] + [c for c in raw.columns if "ownership" in c.lower()], key="micro_ownership_col")
                    if st.button("Optimize multi-entry portfolio"):
                        try:
                            score_matrix = np.asarray(st.session_state["ufi_micro_mc_matrix"], dtype=float)
                            own = None if own_col == "None" else pd.to_numeric(raw[own_col], errors="raise").to_numpy(float)
                            if own is not None and np.nanmax(own) > 1:
                                own = own / 100.0
                            min_positions = json.loads(min_positions_json)
                            max_positions = json.loads(max_positions_json)
                            if not isinstance(min_positions, dict) or not isinstance(max_positions, dict):
                                raise ValueError("Position constraints must be JSON objects")
                            portfolio, report = optimize_fantasyfi_portfolio(
                                raw, score_matrix, ownership=own, budget=budget, roster_size=roster,
                                lineup_count=entries, max_overlap=max_overlap if entries > 1 else None,
                                min_positions=min_positions, max_positions=max_positions
                            )
                            st.dataframe(portfolio, use_container_width=True)
                            st.json(report)
                            st.download_button("Download portfolio CSV", portfolio.to_csv(index=False).encode(), "fantasyfi_microbehavioral_portfolio.csv", "text/csv")
                        except Exception as exc:
                            st.error(f"Portfolio optimization failed: {exc}")
        except Exception as exc:
            st.error(f"Could not read player CSV: {exc}")


elif page == "God-Mode DFS Research Lab":
    st.header("God-Mode DFS Research Lab")
    st.caption("Evidence-first spatial, 300-metric, Dixon-Coles and pre-lock tools. No missing values are fabricated.")
    from src.metric_registry import metric_registry, audit_metric_data
    from src.spatial_kinematics import pitch_geometry, derive_player_kinematics
    from src.prelock_pipeline import validate_prelock_lineups, filter_confirmed_starters
    from src.predictive_models.dixon_coles import fit_dixon_coles, score_grid, match_probabilities

    st.subheader("1. 300-metric coverage audit")
    registry = metric_registry()
    st.write("The registry contains 300 named metrics across six groups. Registry presence is not evidence that a value is available or trained.")
    metric_file = st.file_uploader("Optional player/team/contest dataset CSV to audit", type=["csv"], key="god_metric_csv")
    audit = audit_metric_data(pd.read_csv(metric_file)) if metric_file else registry[["category","metric_number","metric_name","status","used_in_prediction"]]
    st.dataframe(audit, use_container_width=True)
    st.download_button("Download 300-metric registry/audit CSV", audit.to_csv(index=False).encode(), "ufi_300_metric_audit.csv", "text/csv")

    st.divider()
    st.subheader("2. Tracking-derived kinematics")
    pitch_length = float(st.number_input("Pitch length (metres)", min_value=50.0, max_value=130.0, value=105.0, key="god_pitch_l"))
    pitch_width = float(st.number_input("Pitch width (metres)", min_value=30.0, max_value=90.0, value=68.0, key="god_pitch_w"))
    st.json(pitch_geometry(pitch_length, pitch_width))
    tracking_file = st.file_uploader("Tracking CSV: player_id, timestamp, x_m, y_m (optional z_m)", type=["csv"], key="god_tracking_csv")
    if tracking_file:
        if st.button("Calculate observed movement metrics", key="god_run_kinematics"):
            try:
                tracking = pd.read_csv(tracking_file)
                kinematics = derive_player_kinematics(tracking, pitch_length, pitch_width)
                st.dataframe(kinematics, use_container_width=True)
                st.download_button("Download kinematics CSV", kinematics.to_csv(index=False).encode(), "ufi_observed_kinematics.csv", "text/csv")
            except Exception as exc:
                st.error(f"Kinematics failed: {exc}")

    st.divider()
    st.subheader("3. Dixon-Coles scoreline model")
    st.caption("Requires historical match results with date, home_team, away_team, home_goals, away_goals. Evaluate only on chronological holdouts.")
    results_file = st.file_uploader("Historical results CSV", type=["csv"], key="god_dc_csv")
    if results_file:
        try:
            historical = pd.read_csv(results_file)
            teams = sorted(set(historical.get("home_team", pd.Series(dtype=str)).dropna().astype(str)) | set(historical.get("away_team", pd.Series(dtype=str)).dropna().astype(str)))
            if len(teams) >= 2:
                col1, col2 = st.columns(2)
                home_team = col1.selectbox("Home team", teams, key="god_dc_home")
                away_options = [t for t in teams if t != home_team]
                away_team = col2.selectbox("Away team", away_options, key="god_dc_away")
                max_goals = int(st.slider("Maximum goals in each grid dimension", min_value=4, max_value=15, value=10, key="god_dc_cap"))
                if st.button("Fit Dixon-Coles and generate score grid", key="god_run_dc"):
                    try:
                        fit = fit_dixon_coles(historical.to_dict(orient="records"))
                        grid = score_grid(fit, home_team, away_team, max_goals=max_goals)
                        summary = match_probabilities(grid)
                        st.json({"home_team":home_team,"away_team":away_team,"rho":fit.rho,"home_advantage":fit.home_advantage,"time_decay_xi":fit.xi,"summary":summary,"note":"The finite score grid is normalized; tail mass above the chosen cap is omitted."})
                        st.dataframe(pd.DataFrame(grid).round(5), use_container_width=True)
                        st.download_button("Download score grid CSV", pd.DataFrame(grid).to_csv(index=False).encode(), "ufi_dixon_coles_grid.csv", "text/csv")
                    except Exception as exc:
                        st.error(f"Dixon-Coles fit failed: {exc}")
            else:
                st.warning("The CSV must include at least two team names.")
        except Exception as exc:
            st.error(f"Could not read historical results: {exc}")

    st.divider()
    st.subheader("4. Pre-lock lineup validation (60-minute window)")
    st.caption("Upload a source-attributed CSV. The helper checks timestamp freshness and starter labels, but cannot prove that a URL is an official provider.")
    lineup_file = st.file_uploader("Lineup CSV: player_id, team_id, status, source_timestamp, source_url", type=["csv"], key="god_lineup_csv")
    kickoff = st.text_input("Kickoff time with timezone (example 2026-10-22T18:00:00Z)", key="god_kickoff")
    if lineup_file and kickoff:
        if st.button("Validate lineup freshness and starters", key="god_run_lineup"):
            try:
                lineup_data = pd.read_csv(lineup_file)
                validated, report = validate_prelock_lineups(lineup_data, kickoff)
                st.json(report)
                st.dataframe(validated, use_container_width=True)
                st.download_button("Download validated lineup audit", validated.to_csv(index=False).encode(), "ufi_prelock_lineup_audit.csv", "text/csv")
            except Exception as exc:
                st.error(f"Lineup validation failed: {exc}")



elif page == "Data Sources & Calibration Lab":
    st.header("Data Sources & Calibration Lab")
    st.caption("Sourced connectors, source coverage, historical ownership, chronological calibration and joint captain/vice optimization.")
    from src.source_connectors import metric_source_catalog, audit_source_coverage, fetch_statsbomb_competitions, fetch_open_meteo
    from src.probability_calibration import ChronologicalIsotonicCalibrator, chronological_split
    from src.ownership_model import estimate_historical_ownership
    from src.advanced_lineup_optimizer import optimize_captain_vice_lineup, scenario_risk_report

    st.subheader("1. Source plan for all 300 metrics")
    catalog = metric_source_catalog()
    st.write("Each registered metric is mapped to a source family and status. A mapped source is not the same as an observed value.")
    st.dataframe(catalog, use_container_width=True, height=420)
    st.download_button("Download 300-metric source catalog", catalog.to_csv(index=False).encode(), "ufi_300_metric_sources.csv", "text/csv")
    source_data = st.file_uploader("Optional observations CSV for source coverage audit", type=["csv"], key="source_audit_csv")
    if source_data:
        try:
            audit = audit_source_coverage(pd.read_csv(source_data))
            st.dataframe(audit, use_container_width=True)
            st.download_button("Download coverage audit", audit.to_csv(index=False).encode(), "ufi_source_coverage_audit.csv", "text/csv")
        except Exception as exc:
            st.error(f"Source audit failed: {exc}")

    st.divider()
    st.subheader("2. Public StatsBomb data index")
    st.caption("Public selected competitions only; events are not optical tracking. Use the source license/attribution and check competition coverage.")
    if st.button("Fetch StatsBomb Open Data competition index", key="fetch_sb_index"):
        try:
            competitions = fetch_statsbomb_competitions()
            st.dataframe(competitions, use_container_width=True)
            st.download_button("Download competition index", competitions.to_csv(index=False).encode(), "statsbomb_open_data_competitions.csv", "text/csv")
        except Exception as exc:
            st.error(f"StatsBomb index fetch failed: {exc}")

    st.divider()
    st.subheader("3. Weather around kickoff")
    wc1, wc2 = st.columns(2)
    lat = wc1.number_input("Venue latitude", min_value=-90.0, max_value=90.0, value=6.5244, format="%.5f", key="weather_lat")
    lon = wc2.number_input("Venue longitude", min_value=-180.0, max_value=180.0, value=3.3792, format="%.5f", key="weather_lon")
    kickoff_weather = st.text_input("Kickoff with timezone (ISO 8601)", value="2026-10-22T18:00:00Z", key="weather_kickoff")
    if st.button("Fetch Open-Meteo weather", key="fetch_weather"):
        try:
            weather = fetch_open_meteo(lat, lon, kickoff_weather)
            st.json(weather)
            st.download_button("Download weather JSON", json.dumps(weather, indent=2).encode(), "ufi_kickoff_weather.json", "application/json")
        except Exception as exc:
            st.error(f"Weather fetch failed: {exc}")

    st.divider()
    st.subheader("4. Isotonic probability calibration")
    st.caption("CSV columns: date, probability, outcome (0/1). Data is sorted chronologically; the calibrator is fitted on the older training window and evaluated on the untouched later holdout.")
    calibration_file = st.file_uploader("Historical forecast/outcome CSV", type=["csv"], key="calibration_csv")
    train_fraction = st.slider("Training fraction", min_value=0.60, max_value=0.85, value=0.75, step=0.05, key="cal_train_fraction")
    if calibration_file and st.button("Fit and evaluate calibration", key="fit_calibration"):
        try:
            raw = pd.read_csv(calibration_file)
            needed = {"date", "probability", "outcome"}
            if not needed.issubset(raw.columns):
                st.error("Missing columns: " + ", ".join(sorted(needed-set(raw.columns))))
            else:
                train, hold = chronological_split(raw, "date", train_fraction)
                calibrator = ChronologicalIsotonicCalibrator(min_train=100).fit(train.probability, train.outcome, train.date)
                metrics = calibrator.evaluate(hold.probability, hold.outcome)
                st.json({k:v for k,v in metrics.items() if k != "bins"})
                st.dataframe(pd.DataFrame(metrics["bins"]), use_container_width=True)
                hold["calibrated_probability"] = calibrator.predict(hold.probability)
                st.download_button("Download holdout calibrated probabilities", hold.to_csv(index=False).encode(), "ufi_calibrated_holdout.csv", "text/csv")
        except Exception as exc:
            st.error(f"Calibration failed: {exc}")

    st.divider()
    st.subheader("5. Historical contest ownership posterior")
    st.caption("CSV must contain one row per selected player per entry, with entry_id and player_id. Only use contest exports you are authorized to process.")
    ownership_file = st.file_uploader("Contest entry-player CSV", type=["csv"], key="ownership_posterior_csv")
    if ownership_file and st.button("Estimate ownership and credible intervals", key="estimate_ownership"):
        try:
            ownership = estimate_historical_ownership(pd.read_csv(ownership_file))
            st.dataframe(ownership, use_container_width=True)
            st.download_button("Download ownership posterior", ownership.to_csv(index=False).encode(), "ufi_ownership_posterior.csv", "text/csv")
        except Exception as exc:
            st.error(f"Ownership estimation failed: {exc}")

    st.divider()
    st.subheader("6. Joint captain / vice / lineup optimization")
    st.caption("Upload a player slate CSV and a second CSV of jointly simulated scores. The simulation file must have one column per player_id and at least 100 shared scenario rows.")
    slate_file = st.file_uploader("Slate CSV: player_id, position, salary, team_id", type=["csv"], key="captain_slate_csv")
    scenario_file = st.file_uploader("Joint scenario matrix CSV (columns named by player_id)", type=["csv"], key="captain_scenarios_csv")
    oc1, oc2, oc3 = st.columns(3)
    budget = oc1.number_input("Salary budget", min_value=1.0, value=100.0, key="captain_budget")
    roster_size = int(oc2.number_input("Roster size", min_value=1, max_value=30, value=11, key="captain_roster_size"))
    max_team = int(oc3.number_input("Maximum players per team", min_value=1, max_value=30, value=7, key="captain_max_team"))
    if slate_file and scenario_file and st.button("Optimize roster + captain + vice", key="run_joint_captain"):
        try:
            slate = pd.read_csv(slate_file)
            scenarios = pd.read_csv(scenario_file)
            if not set(slate.player_id.astype(str)).issubset(set(scenarios.columns.astype(str))):
                st.error("Scenario CSV needs one column matching every player_id in the slate.")
            else:
                sim = scenarios.loc[:, slate.player_id.astype(str).tolist()].to_numpy(float)
                roster, report = optimize_captain_vice_lineup(slate, sim, budget=budget, roster_size=roster_size, max_per_team=max_team)
                st.json(report)
                st.dataframe(roster, use_container_width=True)
                st.download_button("Download optimized lineup", roster.to_csv(index=False).encode(), "ufi_captain_vice_lineup.csv", "text/csv")
        except Exception as exc:
            st.error(f"Captain/vice optimization failed: {exc}")


else:
    st.header("Data standards & sources")
    st.markdown("""
**Match results:** CSV columns date, home_team, away_team, home_goals, away_goals. One row per completed match, stable team names, ISO dates preferred.

**Contest entries:** CSV columns entry_id, players; player IDs separated by |. Keep contests and slates separate, with platform, salaries, scoring and payout metadata.

**StatsBomb Open Data:** https://github.com/hudl/open-data contains selected competitions/seasons and event, lineup and match JSON. Coverage is selective. Follow the current terms; attribution is required and publication may require additional steps.

**Football-Data.co.uk:** https://www.football-data.co.uk/ provides historical match results and some additional statistics/odds. Check the current terms and column documentation.

No real dataset is bundled or claimed as validated. Historical paid DFS contest entries are not included by default in these football match sources. Obtain them only from a source whose terms permit the intended use.

**Not yet production-ready:** live-data connectors, player tracking/biomechanics, a fitted copula, trained ownership model, exact platform scoring adapters, scalable MIQP, and validated full-field payout optimization. Existing modules remain available; this dashboard is the first integrated control surface, not a final scientific model.
""")
st.divider()
st.caption("UFI · Additive research build · Keep source data and contest terms compliant · Results are uncertain")
