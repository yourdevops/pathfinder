/**
 * Copies vendor JS files from node_modules to ../static/js/vendor/
 * so Django can serve them via {% static %} tags.
 *
 * Skips files whose contents haven't changed so that collectstatic
 * doesn't flag them as modified on every build.
 */
const fs = require('fs');
const path = require('path');

const dest = path.resolve(__dirname, '../static/js/vendor');
fs.mkdirSync(dest, { recursive: true });

const files = [
  ['node_modules/@alpinejs/persist/dist/cdn.min.js', 'alpine-persist.min.js'],
  ['node_modules/@alpinejs/csp/dist/cdn.min.js', 'alpine-csp.min.js'],
  ['node_modules/htmx.org/dist/htmx.min.js', 'htmx.min.js'],
];

files.forEach(([src, target]) => {
  const srcPath = path.resolve(__dirname, src);
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
