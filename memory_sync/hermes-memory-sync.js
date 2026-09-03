/**
 * Hermes Distributed Memory Mirroring Daemon
 * Nodes: MC18, DEV20, VPS (Prime-Projectx)
 * 
 * Automatically keeps USER.md, MEMORY.md, AGENTS.md, and .agents synchronized
 * across all AGY CLI instances via the central VPS hub.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFile } = require('child_process');

const LOCAL_DIR = process.env.USERPROFILE || require('os').homedir();
const REMOTE_USER = 'Prime-Projectx';
const REMOTE_HOST = '103.31.205.218';
const REMOTE_DIR = '/home/Prime-Projectx';
const KEY_PATH = path.join(LOCAL_DIR, '.ssh', 'primeprojectx16.pem');
const SYNCED_FILES = ['USER.md', 'MEMORY.md', 'AGENTS.md'];
const STATE_FILE = path.join(LOCAL_DIR, '.hermes-sync-state.json');

const SSH_BIN = 'C:\\Windows\\System32\\OpenSSH\\ssh.exe';
const SCP_BIN = 'C:\\Windows\\System32\\OpenSSH\\scp.exe';

const POLLING_INTERVAL_MS = 30 * 1000; // Poll VPS every 30s
const DEBOUNCE_DELAY_MS = 2000;         // Debounce local edits by 2s

let state = {
  lastHashes: {},
  lastSyncTime: null
};

// Load persistent state if available
if (fs.existsSync(STATE_FILE)) {
  try {
    state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch (e) {
    state = { lastHashes: {}, lastSyncTime: null };
  }
}

function saveState() {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
  } catch (e) {
    console.error('[STATE] Failed to save state:', e.message);
  }
}

function getLocalHash(filename) {
  const filepath = path.join(LOCAL_DIR, filename);
  if (!fs.existsSync(filepath)) return null;
  const content = fs.readFileSync(filepath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

function getRemoteHashes() {
  return new Promise((resolve) => {
    const remotePaths = SYNCED_FILES.map(f => path.posix.join(REMOTE_DIR, f));
    const args = [
      '-i', KEY_PATH,
      '-o', 'BatchMode=yes',
      '-o', 'ConnectTimeout=8',
      '-o', 'StrictHostKeyChecking=no',
      `${REMOTE_USER}@${REMOTE_HOST}`,
      'sha256sum',
      ...remotePaths
    ];
    execFile(SSH_BIN, args, { timeout: 12000 }, (err, stdout, stderr) => {
      if (err || !stdout) {
        if (err) console.error(`[GET-HASH-ERR]: ${err.message} | STDERR: ${stderr}`);
        return resolve(null);
      }
      const hashes = {};
      stdout.trim().split('\n').forEach(line => {
        const parts = line.trim().split(/\s+/);
        if (parts.length >= 2) {
          const hash = parts[0];
          const fullPath = parts[1];
          const base = path.posix.basename(fullPath);
          hashes[base] = hash;
        }
      });
      resolve(hashes);
    });
  });
}

function pushFile(filename) {
  return new Promise((resolve) => {
    const localFile = path.join(LOCAL_DIR, filename);
    const remoteFile = `${REMOTE_USER}@${REMOTE_HOST}:${path.posix.join(REMOTE_DIR, filename)}`;
    const args = [
      '-i', KEY_PATH,
      '-o', 'BatchMode=yes',
      '-o', 'StrictHostKeyChecking=no',
      localFile,
      remoteFile
    ];
    execFile(SCP_BIN, args, { timeout: 15000 }, (err, stdout, stderr) => {
      if (err) {
        console.error(`[SYNC-ERR] Failed to push ${filename}:`, err.message, stderr);
        return resolve(false);
      }
      const hash = getLocalHash(filename);
      state.lastHashes[filename] = hash;
      state.lastSyncTime = new Date().toISOString();
      saveState();
      console.log(`[SYNC-PUSH] ✅ Successfully mirrored ${filename} -> VPS (${REMOTE_HOST}) [${hash.substring(0, 8)}]`);
      resolve(true);
    });
  });
}

function pullFile(filename, remoteHash) {
  return new Promise((resolve) => {
    const localFile = path.join(LOCAL_DIR, filename);
    const remoteFile = `${REMOTE_USER}@${REMOTE_HOST}:${path.posix.join(REMOTE_DIR, filename)}`;
    const args = [
      '-i', KEY_PATH,
      '-o', 'BatchMode=yes',
      '-o', 'StrictHostKeyChecking=no',
      remoteFile,
      localFile
    ];
    execFile(SCP_BIN, args, { timeout: 15000 }, (err, stdout, stderr) => {
      if (err) {
        console.error(`[SYNC-ERR] Failed to pull ${filename}:`, err.message, stderr);
        return resolve(false);
      }
      state.lastHashes[filename] = remoteHash;
      state.lastSyncTime = new Date().toISOString();
      saveState();
      console.log(`[SYNC-PULL] 📥 Received updated ${filename} <- VPS (${REMOTE_HOST}) [${remoteHash.substring(0, 8)}]`);
      resolve(true);
    });
  });
}

// Full bidirectional verification
async function checkAndSync() {
  const remoteHashes = await getRemoteHashes();
  if (!remoteHashes) {
    console.log(`[SYNC-PING] VPS unreachable or timeout. Retrying next cycle...`);
    return;
  }

  for (const file of SYNCED_FILES) {
    const localHash = getLocalHash(file);
    const remoteHash = remoteHashes[file];

    if (!localHash && remoteHash) {
      // Local missing, pull from remote
      await pullFile(file, remoteHash);
    } else if (localHash && !remoteHash) {
      // Remote missing, push local
      await pushFile(file);
    } else if (localHash && remoteHash && localHash !== remoteHash) {
      // Determine direction by file mtime comparison
      const localStat = fs.statSync(path.join(LOCAL_DIR, file));
      const lastKnown = state.lastHashes[file];

      if (lastKnown === localHash) {
        // Remote has been updated by another node (e.g. DEV20 or VPS directly)
        console.log(`[SYNC-INFO] Remote ${file} was updated by a peer node. Pulling...`);
        await pullFile(file, remoteHash);
      } else {
        // Local has been modified, push to remote
        console.log(`[SYNC-INFO] Local ${file} was modified. Pushing to VPS...`);
        await pushFile(file);
      }
    } else if (localHash && remoteHash && localHash === remoteHash) {
      state.lastHashes[file] = localHash;
    }
  }
  saveState();
}

// Local File Watcher with Debouncing
const debounceTimers = {};

function setupFileWatcher() {
  console.log(`[WATCHER] Monitoring files in ${LOCAL_DIR} for changes: ${SYNCED_FILES.join(', ')}`);

  fs.watch(LOCAL_DIR, (eventType, filename) => {
    if (!filename || !SYNCED_FILES.includes(filename)) return;

    if (debounceTimers[filename]) {
      clearTimeout(debounceTimers[filename]);
    }

    debounceTimers[filename] = setTimeout(async () => {
      const currentHash = getLocalHash(filename);
      if (!currentHash) return;

      if (state.lastHashes[filename] !== currentHash) {
        console.log(`[WATCHER] 🔔 Detected local change in ${filename}. Mirroring to VPS...`);
        await pushFile(filename);
      }
    }, DEBOUNCE_DELAY_MS);
  });
}

// Main execution
async function main() {
  console.log('====================================================');
  console.log('  Hermes Distributed Memory Mirroring Daemon (AGY)  ');
  console.log(`  Local Host: ${process.env.COMPUTERNAME || 'MC18'}`);
  console.log(`  Remote Central Hub: ${REMOTE_USER}@${REMOTE_HOST}`);
  console.log('====================================================');

  // 1. Initial Sync
  console.log('[INIT] Running initial memory check and sync...');
  await checkAndSync();

  // 2. Start File Watcher
  setupFileWatcher();

  // 3. Start Periodic Background Heartbeat
  setInterval(async () => {
    await checkAndSync();
  }, POLLING_INTERVAL_MS);
}

main().catch(err => {
  console.error('[FATAL] Hermes sync error:', err);
});
