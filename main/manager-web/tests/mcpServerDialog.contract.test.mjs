/* eslint-disable test/no-import-node-test -- zero-dependency component contract gate */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const mcpDialogSource = await readFile(
  new URL('../src/components/McpServerDialog.vue', import.meta.url),
  'utf8',
);

test('mcp dialog declares the value/mcpServers/agentId props', () => {
  assert.match(mcpDialogSource, /props:\s*\{[\s\S]*?value:\s*Boolean/);
  assert.match(mcpDialogSource, /mcpServers:\s*\{[\s\S]*?type:\s*Array/);
  assert.match(mcpDialogSource, /agentId:\s*\{[\s\S]*?type:\s*String,[\s\S]*?required:\s*true/);
});

test('mcp dialog emits input / update-mcp-servers / dialog-closed', () => {
  assert.match(mcpDialogSource, /this\.\$emit\('input',/);
  assert.match(mcpDialogSource, /this\.\$emit\('update-mcp-servers', payload\)/);
  assert.match(mcpDialogSource, /this\.\$emit\('dialog-closed'/);
});

test('mcp dialog supports the three transports stdio/sse/streamable-http', () => {
  assert.match(mcpDialogSource, /<el-option label="stdio" value="stdio" \/>/);
  assert.match(mcpDialogSource, /<el-option label="sse" value="sse" \/>/);
  assert.match(mcpDialogSource, /<el-option label="streamable-http" value="streamable-http" \/>/);
});

test('mcp dialog renders command+args for stdio and url for sse/http', () => {
  assert.match(mcpDialogSource, /<template v-if="form\.transport === 'stdio'">/);
  assert.match(mcpDialogSource, /<template v-else>/);
  assert.match(mcpDialogSource, /v-model="form\.command"/);
  assert.match(mcpDialogSource, /v-model="form\.url"/);
});

test('mcp dialog deep-copies incoming servers and coerces field types', () => {
  const watch = mcpDialogSource.slice(
    mcpDialogSource.indexOf('value(v) {'),
    mcpDialogSource.indexOf('dialogVisible(newVal) {'),
  );
  assert.match(watch, /this\.localServers = \(this\.mcpServers \|\| \[\]\)\.map\(/);
  assert.match(watch, /transport: s\.transport \|\| 'stdio'/);
  assert.match(watch, /env: s\.env && typeof s\.env === 'object' \? \{ \.\.\.s\.env \} : \{\}/);
  assert.match(watch, /headers: s\.headers && typeof s\.headers === 'object' \? \{ \.\.\.s\.headers \} : \{\}/);
});

test('mcp dialog confirmEdit validates the name and parses env/headers JSON', () => {
  const confirm = mcpDialogSource.slice(
    mcpDialogSource.indexOf('confirmEdit() {'),
    mcpDialogSource.indexOf('closeDialog() {'),
  );
  assert.match(confirm, /if \(!this\.form\.serverName \|\| !this\.form\.serverName\.trim\(\)\)/);
  assert.match(confirm, /const env = this\.parseJsonField\(this\.envText, \{\}\)/);
  assert.match(confirm, /const headers = this\.parseJsonField\(this\.headersText, \{\}\)/);
  assert.match(confirm, /args =\s*\(this\.argsText \|\| ''\)\s*\.split\('\\n'\)/);
});

test('mcp dialog parseJsonField rejects non-object JSON and surfaces a message', () => {
  const parse = mcpDialogSource.slice(
    mcpDialogSource.indexOf('parseJsonField(text, fallback) {'),
    mcpDialogSource.indexOf('confirmEdit() {'),
  );
  assert.match(parse, /const parsed = JSON\.parse\(text\)/);
  assert.match(parse, /!Array\.isArray\(parsed\) \? parsed : fallback/);
  assert.match(parse, /this\.\$message\.error\(this\.\$t\('mcpServerDialog\.jsonError'\)\)/);
});

test('mcp dialog saveSelection emits a normalized payload with index-based sort', () => {
  const save = mcpDialogSource.slice(
    mcpDialogSource.indexOf('saveSelection() {'),
    mcpDialogSource.indexOf('  }\n};\n</script>'),
  );
  assert.match(save, /const payload = this\.localServers\.map\(\(s, index\) => \(/);
  assert.match(save, /transport: s\.transport \|\| 'stdio',/);
  assert.match(save, /env: s\.env && typeof s\.env === 'object' \? s\.env : \{\},/);
  assert.match(save, /headers: s\.headers && typeof s\.headers === 'object' \? s\.headers : \{\},/);
  assert.match(save, /sort:\s*index/);
  assert.match(save, /this\.\$emit\('update-mcp-servers', payload\)/);
});

test('mcp dialog uses the mcpServerDialog.* i18n namespace', () => {
  const keys = [
    'mcpServerDialog.title',
    'mcpServerDialog.serverNameRequired',
    'mcpServerDialog.jsonError',
    'mcpServerDialog.deleteConfirm',
    'mcpServerDialog.saveConfig',
  ];
  for (const key of keys) {
    assert.match(mcpDialogSource, new RegExp(key.replace('.', '\\.')));
  }
});
