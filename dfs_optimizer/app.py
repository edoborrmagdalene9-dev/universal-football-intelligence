"""Local UFI research dashboard. Run: streamlit run dfs_optimizer/app.py"""
import io, json
import streamlit as st
import pandas as pd
from src.pipeline import load_matches_csv, chronological_backtest, validate_contest_entries_csv
from src.event_simulator import simulate_event_points
from src.continuous_time_states import simulate_score_path

st.set_page_config(page_title="Universal Football Intelligence", page_icon="⚽", layout="wide")
st.title("⚽ Universal Football Intelligence")
st.caption("Local-first football research dashboard · validate before predicting")
st.warning("Research software only. No guaranteed winnings. Demo assumptions are synthetic; do not confuse them with real fixtures.")
page = st.sidebar.radio("Workspace", ["Overview", "Match data & backtest", "Contest ownership", "Event simulation", "Game-state lab", "Data standards"])
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
