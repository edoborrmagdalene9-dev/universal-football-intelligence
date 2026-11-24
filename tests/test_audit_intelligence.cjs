'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={window:{}};
vm.runInNewContext(fs.readFileSync('audit-intelligence.js','utf8'),context,{filename:'audit-intelligence.js'});
const result=context.window.UFI400Audit.evaluate({
 label:'Example selection',odd:2.1,marketType:'1X2',
 fixtureResolution:{status:'candidate-found',matchId:'fixture-1',kickoff:'2026-11-24T18:00:00Z'},
 marketEstimate:{probability:0.52,modelSource:'test-model'},
 signalEvidence:{
  'UFI-001':{status:'ASSESSED',detail:'label checked'},
  'UFI-015':{status:'FETCHED',source:'test bookmaker',detail:'price retrieved'},
  'UFI-022':{status:'ESTIMATED',source:'test model',detail:'model probability'},
  'UFI-101':{status:'NOT_APPLICABLE',detail:'not a corners market'},
  'UFI-102':{status:'PENDING',detail:'source still loading'},
  'UFI-103':{status:'FAIL',detail:'invalid source'}
 }
},{status:'ok'},{});
assert.equal(result.total,400);
assert.equal(result.counts.NOT_APPLICABLE,1);
assert.equal(result.counts.PENDING,1);
assert.equal(result.counts.FAIL,1);
assert.equal(result.evidenceFetched,1);
assert.equal(result.evidenceEstimated,1);
assert.equal(result.notApplicable.length,1);
assert.equal(result.pending.length,1);
assert.equal(result.applicableCoveragePercent>=0,true);
console.log(JSON.stringify({ok:true,total:result.total,counts:result.counts,coveragePercent:result.coveragePercent,applicableCoveragePercent:result.applicableCoveragePercent}));
