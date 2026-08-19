/* eslint-disable test/no-import-node-test -- zero-dependency API regression gate */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const agentApiSource = await readFile(
  new URL('../src/apis/module/agent.js', import.meta.url),
  'utf8',
);

function sourceBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  assert.notEqual(start, -1, `missing source marker: ${startMarker}`);
  assert.notEqual(end, -1, `missing source marker: ${endMarker}`);
  return source.slice(start, end);
}

test('getAgentSkills issues a GET to the per-agent skills endpoint', () => {
  const source = sourceBetween(
    agentApiSource,
    'getAgentSkills(agentId, callback)',
    '// 保存智能体角色级技能配置',
  );
  assert.match(source, /getAgentSkills\(agentId, callback\)/);
  assert.match(source, /\.url\(`\$\{getServiceUrl\(\)\}\/agent\/\$\{agentId\}\/skills`\)/);
  assert.match(source, /\.method\('GET'\)/);
  assert.match(source, /callback\(res\)/);
});

test('saveAgentSkills issues a PUT carrying the skill array directly', () => {
  const source = sourceBetween(
    agentApiSource,
    'saveAgentSkills(agentId, skills, callback)',
    '// 获取智能体角色级MCP服务配置',
  );
  assert.match(source, /saveAgentSkills\(agentId, skills, callback\)/);
  assert.match(source, /\.url\(`\$\{getServiceUrl\(\)\}\/agent\/\$\{agentId\}\/skills`\)/);
  assert.match(source, /\.method\('PUT'\)/);
  assert.match(source, /\.data\(skills\)/);
  assert.doesNotMatch(source, /\.data\(\{[\s\S]*skills[\s\S]*\}\)/);
});

test('getAgentMcpServers issues a GET to the per-agent mcp-servers endpoint', () => {
  const source = sourceBetween(
    agentApiSource,
    'getAgentMcpServers(agentId, callback)',
    '// 保存智能体角色级MCP服务配置',
  );
  assert.match(source, /getAgentMcpServers\(agentId, callback\)/);
  assert.match(source, /\.url\(`\$\{getServiceUrl\(\)\}\/agent\/\$\{agentId\}\/mcp-servers`\)/);
  assert.match(source, /\.method\('GET'\)/);
  assert.match(source, /callback\(res\)/);
});

test('saveAgentMcpServers issues a PUT carrying the server array directly', () => {
  const source = sourceBetween(
    agentApiSource,
    'saveAgentMcpServers(agentId, servers, callback)',
    '    },',
  );
  assert.match(source, /saveAgentMcpServers\(agentId, servers, callback\)/);
  assert.match(source, /\.url\(`\$\{getServiceUrl\(\)\}\/agent\/\$\{agentId\}\/mcp-servers`\)/);
  assert.match(source, /\.method\('PUT'\)/);
  assert.match(source, /\.data\(servers\)/);
  assert.doesNotMatch(source, /\.data\(\{[\s\S]*servers[\s\S]*\}\)/);
});
