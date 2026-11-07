// Fails if a production build still points browsers at a development API.
// Run after `npm run build`: node scripts/check-prod-bundle.mjs
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const EXPECTED_API = "https://api.terrific-bites.trunexus.ai";
const FORBIDDEN = /(localhost|127\.0\.0\.1):80\d\d/g;
const ROOTS = [".output/public/assets", ".output/server"];

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* walk(path);
    else if (/\.m?js$/.test(name)) yield path;
  }
}

const failures = [];
let foundExpected = false;
for (const root of ROOTS) {
  for (const file of walk(root)) {
    const text = readFileSync(file, "utf8");
    for (const match of text.match(FORBIDDEN) ?? []) failures.push(`${file}: ${match}`);
    if (root.includes("public") && text.includes(EXPECTED_API)) foundExpected = true;
  }
}
if (!foundExpected) failures.push(`client bundle does not reference ${EXPECTED_API}`);

if (failures.length) {
  console.error("Production bundle check FAILED:\n" + failures.join("\n"));
  process.exit(1);
}
console.log(`Production bundle check passed: API is ${EXPECTED_API}, no development URLs.`);
