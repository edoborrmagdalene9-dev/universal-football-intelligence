"""Configurable pre-lock lineup validation; no live provider is assumed."""
from datetime import datetime,timezone
import json
from urllib.request import Request,urlopen
import pandas as pd
_REQ={'player_id','team_id','status','source_timestamp','source_url'}
def load_lineup_csv(path):
 d=pd.read_csv(path); missing=_REQ-set(d.columns)
 if missing: raise ValueError('Missing lineup fields: '+', '.join(sorted(missing)))
 return d
def fetch_configured_lineup_json(url,timeout_seconds=10):
 if not url.startswith('https://'): raise ValueError('Endpoint must use HTTPS')
 req=Request(url,headers={'User-Agent':'UniversalFootballIntelligence/1.0','Accept':'application/json'})
 with urlopen(req,timeout=timeout_seconds) as r:
  if r.status!=200: raise RuntimeError(f'Lineup endpoint HTTP {r.status}')
  payload=json.loads(r.read().decode('utf-8'))
 if isinstance(payload,dict): payload=payload.get('players',payload.get('lineups'))
 if not isinstance(payload,list): raise ValueError('Expected JSON list or players/lineups list')
 d=pd.DataFrame(payload); missing=_REQ-set(d.columns)
 if missing: raise ValueError('Endpoint missing fields: '+', '.join(sorted(missing)))
 return d
def validate_prelock_lineups(lineups,kickoff_utc,lock_minutes=60,max_age_minutes=15,now_utc=None,trusted_source_hosts=None):
 missing=_REQ-set(lineups.columns)
 if missing: raise ValueError('Missing lineup fields: '+', '.join(sorted(missing)))
 kickoff=pd.Timestamp(kickoff_utc)
 if kickoff.tzinfo is None: raise ValueError('kickoff_utc must include timezone')
 now=pd.Timestamp(now_utc or datetime.now(timezone.utc)); now=now.tz_localize('UTC') if now.tzinfo is None else now
 minutes=(kickoff.tz_convert('UTC')-now.tz_convert('UTC')).total_seconds()/60; d=lineups.copy(); d['source_timestamp']=pd.to_datetime(d.source_timestamp,errors='coerce',utc=True); age=(now.tz_convert('UTC')-d.source_timestamp).dt.total_seconds()/60
 known=d.status.astype(str).str.lower().isin({'starter','starting','starting_xi','confirmed_starter','bench','substitute','not_selected','injured','unavailable'}); https=d.source_url.astype(str).str.startswith('https://') & d.source_url.notna(); fresh=age.between(-5,max_age_minutes); ids=d.player_id.notna() & d.player_id.astype(str).str.strip().ne(''); from urllib.parse import urlparse; trusted={str(h).lower() for h in (trusted_source_hosts or [])}; trusted_mask=d.source_url.astype(str).map(lambda u:(urlparse(u).hostname or '').lower() in trusted) if trusted else pd.Series(False,index=d.index)
 d['source_host_trusted']=trusted_mask; d['lineup_record_valid']=known & https & fresh & ids & (trusted_mask if trusted else True); d['eligible_for_starting_lineup']=d.lineup_record_valid & d.status.astype(str).str.lower().isin({'starter','starting','starting_xi','confirmed_starter'}); d['eligible_for_substitute_pool']=d.lineup_record_valid & d.status.astype(str).str.lower().isin({'bench','substitute'})
 report={'minutes_to_kickoff':minutes,'lock_window_active':0<=minutes<=lock_minutes,'all_records_valid':bool(d.lineup_record_valid.all()),'invalid_record_count':int((~d.lineup_record_valid).sum()),'starting_players':int(d.eligible_for_starting_lineup.sum()),'bench_players':int(d.eligible_for_substitute_pool.sum()),'source_authority_verified':bool(trusted) and bool(trusted_mask.all()),'trusted_source_hosts':sorted(trusted),'warning':'Only a configured host allowlist provides the runner with a trust gate; independently verify provider authority and licensing.'}; return d,report
def filter_confirmed_starters(players,validated_lineups):
 if 'player_id' not in players: raise ValueError('Players need player_id')
 starters=validated_lineups.loc[validated_lineups.eligible_for_starting_lineup,'player_id'].astype(str)
 return players.loc[players.player_id.astype(str).isin(set(starters))].copy()
