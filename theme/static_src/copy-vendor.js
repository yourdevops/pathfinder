/**
 * Copies vendor JS files from node_modules to ../static/js/vendor/
 * so Django can serve them via {% static %} tags.
 *
 * In development (NODE_ENV != production), copies non-minified versions
 * for easier debugging. In production, copies minified versions.
 *
 * Skips files whose contents haven't changed so that collectstatic
 * doesn't flag them as modified on every build.
 */
const fs = require('fs');
const path = require('path');

const isProd = process.env.NODE_ENV === 'production';
const dest = path.resolve(__dirname, '../static/js/vendor');
fs.mkdirSync(dest, { recursive: true });

// [minified source, non-minified source, output filename]
const files = [
  ['node_modules/@alpinejs/persist/dist/cdn.min.js', 'node_modules/@alpinejs/persist/dist/cdn.js', 'alpine-persist.js'],
  ['node_modules/@alpinejs/csp/dist/cdn.min.js', 'node_modules/@alpinejs/csp/dist/cdn.js', 'alpine-csp.js'],
  ['node_modules/htmx.org/dist/htmx.min.js', 'node_modules/htmx.org/dist/htmx.js', 'htmx.js'],
  ['node_modules/htmx-ext-ws/dist/ws.min.js', 'node_modules/htmx-ext-ws/dist/ws.js', 'htmx-ext-ws.js'],
];

console.log(`  Vendor copy mode: ${isProd ? 'production (minified)' : 'development (non-minified)'}`);

files.forEach(([minSrc, devSrc, target]) => {
  const srcPath = path.resolve(__dirname, isProd ? minSrc : devSrc);
  const destPath = path.resolve(dest, target);

  const srcBuf = fs.readFileSync(srcPath);

  if (fs.existsSync(destPath)) {
    const destBuf = fs.readFileSync(destPath);
    if (srcBuf.equals(destBuf)) {
      console.log(`  Unchanged ${target}`);
      return;
    }
  }

  fs.writeFileSync(destPath, srcBuf);
  console.log(`  Copied ${target}`);
});
