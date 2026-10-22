import pandas as pd
from dfs_optimizer.src.metric_registry import metric_registry
from dfs_optimizer.src.source_connectors import metric_source_catalog, audit_source_coverage, statsbomb_events_to_tracking
from dfs_optimizer.src.research_source_catalog import source_register

def test_all_300_metrics_have_source_strategy_and_status():
    reg=metric_registry(); cat=metric_source_catalog()
    assert len(cat)==300 and cat.metric_name.is_unique
    assert set(reg.metric_name)==set(cat.metric_name)
    assert cat.source_family.notna().all() and cat.acquisition_status.notna().all()
    assert (cat.currently_populated==False).all()
    assert len(source_register())>=10

def test_source_coverage_audit_distinguishes_present_from_populated():
    d=audit_source_coverage(pd.DataFrame({'pitch_length_m':[105,None]}))
    row=d.loc[d.metric_name=='pitch_length_m'].iloc[0]
    assert row.present_in_input and row.non_null_count==1
    assert not d.loc[d.metric_name=='sprint_speed_peak_mps','present_in_input'].iloc[0]

def test_statsbomb_event_locations_are_not_mislabeled_as_tracking():
    events=pd.DataFrame({'player.id':[1,2],'timestamp':['00:00:01.000','00:00:02.000'],'location':[[60,40],[30,20]]})
    out=statsbomb_events_to_tracking(events)
    assert len(out)==2 and set(out.source_type)=={'event_location_not_tracking'}
