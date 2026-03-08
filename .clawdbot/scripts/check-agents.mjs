#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repoRoot = process.cwd();
const registryPath = path.join(repoRoot, '.clawdbot', 'active-tasks.json');

function hasCmd(cmd) {
  const p = spawnSync('bash', ['-lc', `command -v ${cmd}`], { stdio: 'ignore' });
  return p.status === 0;
}

function run(cmd, args, cwd = repoRoot) {
  return spawnSync(cmd, args, { cwd, encoding: 'utf8' });
}

function loadRegistry() {
  if (!fs.existsSync(registryPath)) {
    return { version: 1, updatedAt: null, tasks: [] };
  }
  try {
    const data = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
    if (!Array.isArray(data.tasks)) data.tasks = [];
    return data;
  } catch {
    return { version: 1, updatedAt: null, tasks: [] };
  }
}

function parseCiFromRollup(rollup) {
  if (!Array.isArray(rollup) || rollup.length === 0) return 'unknown';
  let hasPending = false;
  for (const item of rollup) {
    const conclusion = String(item?.conclusion || '').toUpperCase();
    const status = String(item?.status || '').toUpperCase();
    if (['FAILURE', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'ACTION_REQUIRED'].includes(conclusion)) {
      return 'failed';
    }
    if (['PENDING', 'IN_PROGRESS', 'QUEUED', 'WAITING'].includes(status)) {
      hasPending = true;
    }
  }
  return hasPending ? 'pending' : 'passed';
}

function getPrInfo(branch) {
  if (!hasCmd('gh')) return { prNumber: null, prUrl: null, ci: 'unknown' };

  const list = run('gh', ['pr', 'list', '--head', branch, '--json', 'number,url,state,isDraft', '--limit', '1']);
  if (list.status !== 0 || !list.stdout.trim()) return { prNumber: null, prUrl: null, ci: 'unknown' };

  let prs = [];
  try { prs = JSON.parse(list.stdout); } catch {}
  const first = prs?.[0];
  if (!first?.number) return { prNumber: null, prUrl: null, ci: 'unknown' };

  const view = run('gh', ['pr', 'view', String(first.number), '--json', 'statusCheckRollup,url']);
  let ci = 'unknown';
  let prUrl = first.url || null;
  if (view.status === 0 && view.stdout.trim()) {
    try {
      const detail = JSON.parse(view.stdout);
      ci = parseCiFromRollup(detail.statusCheckRollup);
      prUrl = detail.url || prUrl;
    } catch {}
  }

  return { prNumber: first.number, prUrl, ci };
}

function isSessionAlive(sessionName) {
  if (!sessionName || !hasCmd('tmux')) return false;
  const p = run('tmux', ['has-session', '-t', sessionName]);
  return p.status === 0;
}

function readLastExitCodeFromLog(taskId) {
  const logPath = path.join(repoRoot, '.clawdbot', 'logs', `${taskId}.log`);
  if (!fs.existsSync(logPath)) return null;

  try {
    const content = fs.readFileSync(logPath, 'utf8');
    const matches = [...content.matchAll(/exit_code=(\d+)/g)];
    if (matches.length === 0) return null;
    const code = Number(matches[matches.length - 1][1]);
    return Number.isNaN(code) ? null : code;
  } catch {
    return null;
  }
}

function notify(text) {
  if (!hasCmd('openclaw')) return;
  run('openclaw', ['system', 'event', '--text', text, '--mode', 'now']);
}

const registry = loadRegistry();
const now = Date.now();

for (const task of registry.tasks) {
  if (!task?.id) continue;

  const prevStatus = task.status || 'unknown';
  const sessionAlive = isSessionAlive(task.tmuxSession);
  const { prNumber, prUrl, ci } = getPrInfo(task.branch);

  task.pr = prNumber ?? task.pr ?? null;
  task.prUrl = prUrl ?? task.prUrl ?? null;
  task.ci = ci;

  let nextStatus = prevStatus;
  let note = task.note || '';

  if (sessionAlive) {
    nextStatus = 'running';
    note = 'tmux session alive';
  } else if (prNumber) {
    if (ci === 'passed') {
      nextStatus = 'done';
      note = 'PR exists and CI passed';
    } else if (ci === 'failed') {
      nextStatus = 'failed';
      note = 'PR exists but CI failed';
    } else {
      nextStatus = 'waiting_ci';
      note = 'PR exists, waiting CI';
    }
  } else if (['running', 'retrying', 'waiting_ci'].includes(prevStatus)) {
    const lastExitCode = readLastExitCodeFromLog(task.id);
    if (lastExitCode === 0) {
      nextStatus = 'done_local';
      note = 'Local task completed successfully (no PR)';
    } else {
      nextStatus = 'failed';
      note = 'tmux session ended before PR creation';
    }
  }

  task.status = nextStatus;
  task.updatedAt = now;
  task.note = note;

  if (prevStatus !== nextStatus && task.notifyOnComplete) {
    if (nextStatus === 'done') {
      notify(`✅ ${task.id} done: PR #${task.pr ?? '?'} is ready.`);
    } else if (nextStatus === 'done_local') {
      notify(`✅ ${task.id} done_local: task finished successfully without PR.`);
    } else if (nextStatus === 'failed') {
      notify(`⚠️ ${task.id} failed: ${note}`);
    }
  }
}

registry.updatedAt = now;
fs.writeFileSync(registryPath, JSON.stringify(registry, null, 2));

const lines = registry.tasks.map(t => {
  const pr = t.pr ? `#${t.pr}` : '-';
  return `${t.id}\t${t.status}\t${pr}\t${t.ci ?? '-'}\t${t.note ?? ''}`;
});

console.log('task_id\tstatus\tpr\tci\tnote');
for (const line of lines) console.log(line);
