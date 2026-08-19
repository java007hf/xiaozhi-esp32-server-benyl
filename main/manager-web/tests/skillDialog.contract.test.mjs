/* eslint-disable test/no-import-node-test -- zero-dependency component contract gate */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const skillDialogSource = await readFile(
  new URL('../src/components/SkillDialog.vue', import.meta.url),
  'utf8',
);

test('skill dialog declares the value/skills/agentId props', () => {
  assert.match(skillDialogSource, /props:\s*\{[\s\S]*?value:\s*Boolean/);
  assert.match(skillDialogSource, /skills:\s*\{[\s\S]*?type:\s*Array/);
  assert.match(skillDialogSource, /agentId:\s*\{[\s\S]*?type:\s*String,[\s\S]*?required:\s*true/);
});

test('skill dialog emits input / update-skills / dialog-closed', () => {
  assert.match(skillDialogSource, /this\.\$emit\('input',/);
  assert.match(skillDialogSource, /this\.\$emit\('update-skills', payload\)/);
  assert.match(skillDialogSource, /this\.\$emit\('dialog-closed'/);
});

test('skill dialog deep-copies incoming skills and coerces field types', () => {
  const watch = skillDialogSource.slice(
    skillDialogSource.indexOf('value(v) {'),
    skillDialogSource.indexOf('dialogVisible(newVal) {'),
  );
  assert.match(watch, /this\.localSkills = \(this\.skills \|\| \[\]\)\.map\(/);
  assert.match(watch, /Array\.isArray\(s\.functions\) \? \[\.\.\.s\.functions\] : \(s\.functions \|\| \[\]\)/);
  assert.match(watch, /s\.files && typeof s\.files === 'object' \? \{ \.\.\.s\.files \} : \{\}/);
  assert.match(watch, /enabled: s\.enabled === undefined \? true : !!s\.enabled/);
});

test('skill dialog confirmEdit validates the name and parses files JSON', () => {
  const confirm = skillDialogSource.slice(
    skillDialogSource.indexOf('confirmEdit() {'),
    skillDialogSource.indexOf('closeDialog() {'),
  );
  assert.match(confirm, /if \(!this\.form\.skillName \|\| !this\.form\.skillName\.trim\(\)\)/);
  assert.match(confirm, /const parsed = JSON\.parse\(this\.filesText\)/);
  assert.match(confirm, /this\.\$message\.error\(this\.\$t\('skillDialog\.jsonError'\)\)/);
  assert.match(confirm, /functions =\s*\(this\.functionsText \|\| ''\)\s*\.split\('\\n'\)/);
});

test('skill dialog saveSelection emits a normalized payload with index-based sort', () => {
  const save = skillDialogSource.slice(
    skillDialogSource.indexOf('saveSelection() {'),
    skillDialogSource.indexOf('  }\n};\n</script>'),
  );
  assert.match(save, /const payload = this\.localSkills\.map\(\(s, index\) => \(/);
  assert.match(save, /functions: Array\.isArray\(s\.functions\) \? s\.functions : \[\],/);
  assert.match(save, /files: s\.files && typeof s\.files === 'object' \? s\.files : \{\},/);
  assert.match(save, /enabled: s\.enabled === undefined \? true : !!s\.enabled,/);
  assert.match(save, /sort:\s*index/);
  assert.match(save, /this\.\$emit\('update-skills', payload\)/);
});

test('skill dialog uses the skillDialog.* i18n namespace', () => {
  const keys = [
    'skillDialog.title',
    'skillDialog.skillNameRequired',
    'skillDialog.jsonError',
    'skillDialog.deleteConfirm',
    'skillDialog.saveConfig',
  ];
  for (const key of keys) {
    assert.match(skillDialogSource, new RegExp(key.replace('.', '\\.')));
  }
});
