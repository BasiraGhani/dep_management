#!/usr/bin/env node
/**
 * Checks that package-lock.json is complete: every dependency of every locked
 * package resolves to a locked entry, the way Node looks packages up (the nearest
 * node_modules folder, then each parent's).
 *
 * Why: `npm install` on macOS sometimes drops entries that only Linux needs (e.g.
 * @emnapi/core for the wasm builds of rolldown and Tailwind). The lock file still
 * names them but no longer says where they are, and `npm ci` then fails on Linux
 * (CI, Docker) with a confusing error. This reports it plainly instead.
 *
 *   npm run check:lock                  # check (CI runs this before npm ci)
 *   npm run check:lock -- --fix         # copy missing entries from origin/main's lock
 *   npm run check:lock -- --fix=<ref>   # ... or from another git ref
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const LOCK = fileURLToPath(new URL('../package-lock.json', import.meta.url));

/** Where Node would find `name` when required from the package at `path`. */
function candidates(path, name) {
  const places = [];
  let dir = path;
  for (;;) {
    places.push(dir ? `${dir}/node_modules/${name}` : `node_modules/${name}`);
    const at = dir.lastIndexOf('/node_modules/');
    if (at === -1) {
      if (dir === '') break;
      dir = '';
    } else {
      dir = dir.slice(0, at);
    }
  }
  return places;
}

/** Dependencies of each entry that resolve to nothing: [{ from, name, expected }]. */
export function missingEntries(packages) {
  const missing = [];
  for (const [path, entry] of Object.entries(packages)) {
    if (entry.link || entry.inBundle) continue;
    const optionalPeers = entry.peerDependenciesMeta ?? {};
    const names = [
      ...Object.keys(entry.dependencies ?? {}),
      ...Object.keys(entry.optionalDependencies ?? {}),
      ...Object.keys(entry.peerDependencies ?? {}).filter((n) => !optionalPeers[n]?.optional),
    ];
    for (const name of new Set(names)) {
      const places = candidates(path, name);
      // An optional dependency for another platform may be absent on purpose
      // only if npm never listed it; listed-but-unresolvable is the bug we catch.
      if (!places.some((place) => place in packages)) {
        missing.push({ from: path || '(root)', name, expected: places.at(-1) });
      }
    }
  }
  return missing;
}

/** Insert entries into `packages`, keeping npm's alphabetical order of keys. */
function withEntries(packages, additions) {
  const keys = [...Object.keys(packages), ...Object.keys(additions)];
  const [root, ...rest] = keys;
  rest.sort((a, b) => a.localeCompare(b, 'en'));
  return Object.fromEntries([root, ...rest].map((key) => [key, packages[key] ?? additions[key]]));
}

function main() {
  const text = readFileSync(LOCK, 'utf8');
  const lock = JSON.parse(text);
  const missing = missingEntries(lock.packages);
  if (missing.length === 0) {
    console.log('package-lock.json is complete.');
    return 0;
  }

  const fixArg = process.argv.find((arg) => arg.startsWith('--fix'));
  if (!fixArg) {
    console.error('package-lock.json is incomplete: these dependencies resolve to nothing.');
    for (const m of missing) console.error(`  ${m.from} needs ${m.name} (no ${m.expected})`);
    console.error(
      '\nThis usually happens after `npm install` on macOS. Fix it with:\n' +
        '  npm run check:lock -- --fix   (copies the entries from origin/main)',
    );
    return 1;
  }

  const ref = fixArg.includes('=') ? fixArg.split('=')[1] : 'origin/main';
  const base = JSON.parse(
    execFileSync('git', ['show', `${ref}:frontend/package-lock.json`], { encoding: 'utf8' }),
  ).packages;
  const additions = {};
  for (const { expected } of missing) {
    if (base[expected]) additions[expected] = base[expected];
  }
  const stillMissing = missingEntries(withEntries(lock.packages, additions));
  if (stillMissing.length > 0) {
    console.error(`${ref} doesn't have every missing entry either:`);
    for (const m of stillMissing) console.error(`  ${m.from} needs ${m.name}`);
    console.error('Run `npm install` on Linux (or in the node:24-slim Docker image) instead.');
    return 1;
  }
  lock.packages = withEntries(lock.packages, additions);
  writeFileSync(LOCK, `${JSON.stringify(lock, null, 2)}\n`);
  console.log(`Restored from ${ref}: ${Object.keys(additions).join(', ')}`);
  return 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.exit(main());
}
