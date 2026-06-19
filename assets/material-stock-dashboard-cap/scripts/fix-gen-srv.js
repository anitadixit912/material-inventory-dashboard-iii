#!/usr/bin/env node
/**
 * Post-build script: patches gen/srv/package.json to use SQLite instead of
 * HANA, and copies React dist + mock data into gen/srv so the platform image
 * contains everything needed to run.
 */
const fs   = require('fs');
const path = require('path');

const root     = path.join(__dirname, '..');
const genSrv   = path.join(root, 'gen', 'srv');

// ── 1. Patch gen/srv/package.json ──────────────────────────────────────────
const pkgPath = path.join(genSrv, 'package.json');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

// Remove HANA, add SQLite
delete pkg.dependencies['@cap-js/hana'];
pkg.dependencies['@cap-js/sqlite'] = '^2.4';

// Remove @sap/xssec — prevents CAP from auto-enabling XSUAA JWT validation.
// Authentication is handled by the platform gateway; the app runs open internally.
delete pkg.dependencies['@sap/xssec'];

// Ensure cds config exists
pkg.cds = pkg.cds || {};
pkg.cds.requires = pkg.cds.requires || {};

// Remove any environment-specific auth override buried inside cds.requires
// (CDS build sometimes emits cds.requires['[production]'].auth = 'xsuaa')
if (pkg.cds.requires['[production]']) {
  delete pkg.cds.requires['[production]'].auth;
}

// Set auth: dummy unconditionally at cds.requires level.
// CDS 9 activates [production] profile blocks only when CDS_ENV=production (not NODE_ENV),
// so we set auth at the top-level requires to ensure it is always respected.
pkg.cds.requires.auth = { kind: 'dummy' };

// Set top-level production overrides: SQLite DB + dummy auth (no JWT validation)
pkg.cds['[production]'] = {
  requires: {
    db: {
      kind: 'sqlite',
      credentials: { url: '/app/db.sqlite' }
    },
    auth: 'dummy'
  }
};

fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');
console.log('[fix-gen-srv] Patched gen/srv/package.json: SQLite + dummy auth for production.');

// ── 2. Copy React dist → gen/srv/app/react-ui/dist ─────────────────────────
function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

const reactSrc  = path.join(root, 'app', 'react-ui', 'dist');
const reactDest = path.join(genSrv, 'app', 'react-ui', 'dist');
if (fs.existsSync(reactSrc)) {
  copyDir(reactSrc, reactDest);
  console.log('[fix-gen-srv] Copied React dist → gen/srv/app/react-ui/dist');
} else {
  console.warn('[fix-gen-srv] WARNING: app/react-ui/dist not found — run npm run build:ui first');
}

// ── 3. Copy mock data → gen/srv/test/data ──────────────────────────────────
const mockSrc  = path.join(root, 'test', 'data', 'material-stock-mock.js');
const mockDest = path.join(genSrv, 'test', 'data', 'material-stock-mock.js');
if (fs.existsSync(mockSrc)) {
  fs.mkdirSync(path.dirname(mockDest), { recursive: true });
  fs.copyFileSync(mockSrc, mockDest);
  console.log('[fix-gen-srv] Copied mock data → gen/srv/test/data/');
}
