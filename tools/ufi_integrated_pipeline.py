#!/usr/bin/env python3
"""Run UFI's coordinated Phase 1–3 research pipeline with explicit evidence gates."""
from __future__ import annotations
import argparse, csv, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER_FIELDS = {"player_name","source_name","source_url","preferred_foot","weak_foot_evidence","role","observed_style_tags","efootball_style_tags","confidence_0_to_1","record_type"}
VALID_FEET = {"left","right","both","unknown"}

def audit_player_registry(path: Path) -> dict:
    if not path.is_file():
        return {"file":str(path),"exists":False,"records":0,"status":"missing","errors":[],"warnings":["No registry CSV supplied."],"footedness_known_records":0,"weak_foot_evidence_records":0,"style_tagged_records":0,"efootball_tagged_records":0,"used_as_prediction_feature":False}
    with path.open(encoding="utf-8-sig",newline="") as handle:
        reader=csv.DictReader(handle); headers=set(reader.fieldnames or [])
        rows=[r for r in reader if (r.get("player_name") or "").strip()]
    missing=sorted(PLAYER_FIELDS-headers); errors=[]; warnings=[]
    feet=weak=styles=game_styles=0
    for line,row in enumerate(rows,start=2):
        foot=(row.get("preferred_foot") or "unknown").strip().lower()
        if foot not in VALID_FEET: errors.append(f"Row {line}: invalid preferred_foot '{foot}'.")
        if foot in {"left","right","both"}: feet+=1
        if (row.get("weak_foot_evidence") or "").strip(): weak+=1
        if (row.get("observed_style_tags") or "").strip(): styles+=1
        if (row.get("efootball_style_tags") or "").strip(): game_styles+=1
        if not (row.get("source_name") or "").strip() or not (row.get("source_url") or "").strip():
            warnings.append(f"Row {line}: source provenance missing; do not treat claims as verified.")
        try:
            confidence=float(row.get("confidence_0_to_1") or "")
            if not 0 <= confidence <= 1: raise ValueError()
        except ValueError: warnings.append(f"Row {line}: confidence_0_to_1 missing or outside 0–1.")
    if missing: errors.append("Missing required headers: "+", ".join(missing))
    if not rows: warnings.append("Registry has no player records; player-aware prediction is disabled.")
    status="validated_with_current_checks" if rows and not errors and not warnings else ("needs_correction" if errors else "needs_evidence_or_more_records")
    return {"file":str(path),"exists":True,"records":len(rows),"status":status,"errors":errors,"warnings":warnings,"footedness_known_records":feet,"weak_foot_evidence_records":weak,"style_tagged_records":styles,"efootball_tagged_records":game_styles,"required_headers_present":not missing,"used_as_prediction_feature":False,"reason_not_used":"OpenFootball results do not identify lineups or player minutes; player claims are not joined to fixtures without verified player-match participation data."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--matches",default="output/openfootball/matches.csv")
    p.add_argument("--out",default="output/openfootball/integrated")
    p.add_argument("--player-registry",default="data/private/player_registry.csv")
    p.add_argument("--odds-csv",default="data/private/pre_match_odds.csv")
    p.add_argument("--skip-advanced",action="store_true")
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    advanced_out=out/"advanced"; odds_path=Path(a.odds_csv); player_path=Path(a.player_registry)
    if not player_path.is_file(): player_path=ROOT/"data/templates/player_registry_template.csv"
    if not a.skip_advanced:
        cmd=[sys.executable,str(ROOT/"tools/ufi_advanced_backtest.py"),"--input",str(Path(a.matches)),"--out",str(advanced_out)]
        if odds_path.is_file() and odds_path.stat().st_size>0: cmd += ["--odds-csv",str(odds_path)]
        subprocess.run(cmd,check=True)
    metrics_path=advanced_out/"metrics.json"
    if not metrics_path.is_file(): raise SystemExit(f"Advanced metrics not found: {metrics_path}")
    m=json.loads(metrics_path.read_text(encoding="utf-8")); players=audit_player_registry(player_path)
    odds_supplied=odds_path.is_file() and odds_path.stat().st_size>0
    market_audit={"status":"not_run_no_odds_supplied"}
    if odds_supplied:
        audit_out=out/"market_audit"
        audit_cmd=[sys.executable,str(ROOT/"tools/ufi_probability_market_audit.py"),
                   "--predictions",str(advanced_out/"advanced_predictions.csv"),
                   "--odds-csv",str(odds_path),"--out",str(audit_out)]
        audit_run=subprocess.run(audit_cmd,check=False,capture_output=True,text=True)
        audit_json=audit_out/"probability_market_audit.json"
        if audit_json.is_file():
            market_audit=json.loads(audit_json.read_text(encoding="utf-8"))
            market_audit["status"]="completed" if market_audit.get("matched_scored_fixtures",0)>0 else "no_matched_fixtures"
        else:
            market_audit={"status":"failed_to_write_report","return_code":audit_run.returncode,
                          "error":(audit_run.stderr or "")[-1000:]}
    models=m.get("models",{})
    phase1={"status":"evaluated","backtested_matches":m.get("backtested_matches",0),"models":models,"same_date_leakage_control":m.get("same_date_leakage_control","")}
    phase2_status="player evidence available for future integration" if players["records"] else "blocked_pending_sourced_player_records"
    phase2={"status":phase2_status,"registry_audit":players,"prediction_integration":"disabled until player-to-match participation, minutes, and pre-kickoff availability are verified"}
    phase3={"status":"paper_test_completed_with_supplied_odds" if m.get("paper_bet_count",0) else ("odds_supplied_but_no_matches_joined" if odds_supplied else "ready_but_no_odds_supplied"),"odds_file_supplied":odds_supplied,"odds_status":m.get("odds_status"),"paper_bet_count":m.get("paper_bet_count",0),"paper_profit_units":m.get("paper_profit_units"),"paper_roi":m.get("paper_roi"),"probability_market_audit":market_audit,"warning":"Retrospective paper results are not evidence of future profitability. Quotes must be captured before kickoff and source terms must permit this use."}
    report={"project":"Universal Football Intelligence","pipeline":"integrated Phase 1 + Phase 2 evidence audit + Phase 3 paper-validation gate","phase_1_match_model":phase1,"phase_2_player_intelligence":phase2,"phase_3_odds_validation":phase3,"probability_market_audit":market_audit,"limitations":["Results-only OpenFootball data cannot provide player footedness, play style, lineups, substitutions or tracking.","Player registry fields are audited but not used as forecast features until player-match participation and timing are verified.","ROI is not computed unless timestamped, authorized odds are supplied.","Accuracy alone does not establish profitability; compare Brier score, log loss, market baselines and multiple chronological periods."]}
    (out/"ufi_integrated_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    ens=models.get("fixed_elo_plus_poisson_ensemble",{}); elo=models.get("elo_only",{}); base=models.get("league_frequency_baseline",{})
    lines=["# UFI integrated research report","","All three phases are coordinated in one pipeline. Status distinguishes tested components from data-gated components.","","## Phase 1 — match prediction",f"- Eligible historical matches: {phase1['backtested_matches']:,}",f"- Elo + Poisson ensemble accuracy: {ens.get('accuracy')}",f"- Elo-only accuracy: {elo.get('accuracy')}",f"- Historical league baseline accuracy: {base.get('accuracy')}",f"- Leakage control: {phase1['same_date_leakage_control']}","","## Phase 2 — player intelligence",f"- Status: {phase2_status}",f"- Registry records: {players['records']}",f"- Records with known foot: {players['footedness_known_records']}",f"- Records with weak-foot evidence: {players['weak_foot_evidence_records']}",f"- Records with observed style tags: {players['style_tagged_records']}","- Player attributes are not fed into predictions without verified player-match participation data.","","## Phase 3 — paper validation",f"- Status: {phase3['status']}",f"- Odds status: {phase3['odds_status']}",f"- Paper bets: {phase3['paper_bet_count']}",f"- Paper profit (units): {phase3['paper_profit_units']}",f"- Paper ROI: {phase3['paper_roi']}","","## Important limitations",*[f"- {x}" for x in report["limitations"]],"","Machine-readable detail: ufi_integrated_report.json; model predictions and ledger are in the advanced/ subfolder."]
    (out/"ufi_integrated_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"report_json":str(out/"ufi_integrated_report.json"),"report_markdown":str(out/"ufi_integrated_report.md"),"phase_1":phase1["status"],"phase_2":phase2_status,"phase_3":phase3["status"],"player_records":players["records"],"paper_bets":phase3["paper_bet_count"]},indent=2))

if __name__=="__main__": main()
