const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const app = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

assert.match(app, /initUfiTelemetry\(\)/);
assert.match(app, /ufi_app_loaded/);
assert.match(app, /ufi_action/);
assert.match(app, /autocapture:\s*false/);
assert.match(app, /disable_session_recording:\s*true/);
assert.match(app, /persistence:\s*'memory'/);
assert.match(app, /person_profiles:\s*'never'/);
assert.match(app, /ufiRunEndToEndPipeline/);
assert.match(html, /app\.js\?v=ufi-posthog-20261028-1/);
console.log('PASS: anonymous opt-in event allowlist is enabled; autocapture and session recording stay off.');
