const child_process = require('child_process');
const fs = require('fs');

function run(cmd) {
  console.log('$ ' + cmd);
  child_process.execSync(cmd, { stdio: 'inherit', env: process.env });
}

function capture(cmd) {
  return child_process
    .execSync(cmd, { encoding: 'utf8', env: process.env })
    .toString();
}

function verifyToken(token) {
  try {
    const output = capture(
      `curl -s -H "Authorization: Bearer ${token}" https://api.github.com/user`
    );
    const data = JSON.parse(output);
    if (data.login) {
      console.log(`Authenticated with GitHub API as ${data.login}`);
    } else {
      console.warn('GitHub API did not return user information');
    }
  } catch (e) {
    console.warn('GitHub API request failed: ' + e.message);
  }
}

function loadCredentials() {
  let token = process.env.GITHUB_TOKEN;
  let remote = process.env.GITHUB_REMOTE;
  if (!token || !remote) {
    try {
      const config = JSON.parse(fs.readFileSync('config.json', 'utf8'));
      token = token || config.token;
      remote = remote || config.remote;
    } catch (e) {
      // ignore missing config file for now
    }
  }
  if (!token || !remote) {
    console.error(
      'GitHub token and remote URL must be provided via environment variables or config.json'
    );
    process.exit(1);
  }
  return { token, remote };
}

function main() {
  const { token, remote } = loadCredentials();
  verifyToken(token);
  const url = remote.replace(/^https?:\/\//, `https://${token}@`);
  try {
    run(`git pull ${url} --rebase`);
  } catch (e) {
    const strategy = process.env.GIT_AUTOMERGE;
    if (strategy === 'ours' || strategy === 'theirs') {
      console.warn(`Pull failed. Attempting ${strategy} auto-merge.`);
      try {
        run('git rebase --abort || true');
        run(`git fetch ${url}`);
        const branch = capture('git rev-parse --abbrev-ref HEAD').trim();
        run(`git merge -X ${strategy} origin/${branch}`);
      } catch (mergeErr) {
        console.error('Auto-merge failed. Resolve conflicts manually.');
        process.exit(1);
      }
    } else {
      console.error('Pull failed. Resolve conflicts and run again.');
      process.exit(1);
    }
  }
  try {
    run('git add -A');
    run('git commit -m "Auto commit by Hecate"');
  } catch (e) {
    console.log('Nothing to commit');
  }
  run(`git push ${url}`);
}

if (require.main === module) {
  main();
}

module.exports = { verifyToken, run, capture, main };

