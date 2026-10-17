const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const script = fs.readFileSync('ai-council.js', 'utf8');

function makeHarness({failGroq = false} = {}) {
  const elements = new Map();
  const calls = [];
  const attached = [];
  const get = id => {
    if (!elements.has(id)) {
      elements.set(id, {id, value:'', textContent:'', innerHTML:'', disabled:false, handlers:{},
        addEventListener(name, fn) { this.handlers[name] = fn; }});
    }
    return elements.get(id);
  };
  for (const [id,value] of Object.entries({
    aiGeminiKey:'gemini-test-key', aiGeminiModel:'gemini-test-model',
    aiGroqKey:'groq-test-key', aiGroqModel:'groq-test-model',
    aiOpenRouterKey:'router-test-key', aiOpenRouterModel:'router-test-model',
    aiHfKey:'hf-test-key', aiHfModel:'hf-test-model'
  })) get(id).value = value;
  const payload = {overall_status:'HOLD',summary:'Test-only advisory',traps:[],missing_evidence:['Test data only'],model_limitations:[],replacement_readiness:'NONE QUALIFIED',disagreements:[],questions_to_verify:[]};
  const okResponse = (data) => ({ok:true,status:200,text:async()=>JSON.stringify(data)});
  const context = {
    document:{getElementById:get},
    window:{UFI_AI_CONTEXT:()=>({testFixture:true, dataInventory:{eventsLoaded:0}}),UFI_ATTACH_AI_COUNCIL:r=>attached.push(r)},
    location:{origin:'https://test.invalid'},
    fetch:async (url,options)=>{
      calls.push({url,options});
      if(failGroq && url.includes('api.groq.com')) return {ok:false,status:429,text:async()=>JSON.stringify({error:{message:'rate limit test'}})};
      if(url.includes('generativelanguage.googleapis.com')) return okResponse({candidates:[{content:{parts:[{text:JSON.stringify(payload)}]}}]});
      return okResponse({choices:[{message:{content:JSON.stringify(payload)}}]});
    },
    AbortController, setTimeout, clearTimeout, Date, JSON, String, Number, Array, Object, Math, Error, Promise
  };
  vm.runInNewContext(script, context, {filename:'ai-council.js'});
  return {elements,get,calls,attached};
}

(async()=>{
  const normal=makeHarness();
  await normal.get('runAiCouncil').handlers.click();
  assert.equal(normal.calls.length,3,'three configured providers should run in parallel when all succeed');
  assert.equal(normal.attached[0].successfulModels,3,'all three parallel responses should be counted');
  assert.equal(normal.attached[0].fallbackUsed,null,'fallback should not run when three primary providers succeed');

  const failover=makeHarness({failGroq:true});
  await failover.get('runAiCouncil').handlers.click();
  assert.equal(failover.calls.length,4,'fourth provider should be called after one of the first three fails');
  assert.equal(failover.attached[0].successfulModels,3,'fallback should restore three successful model opinions');
  assert.equal(failover.attached[0].fallbackUsed,'Hugging Face','the configured spare provider should be recorded');
  assert.equal(failover.attached[0].models.find(m=>m.provider==='Groq').status,'failed','failed provider should be visible');
  console.log('AI council smoke tests passed: 3-way parallel execution and provider failover.');
})().catch(err=>{console.error(err);process.exitCode=1;});
