import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const ROOT = process.cwd();
const ADDONS_DIR = path.join(ROOT, "addons");

function isDir(p) {
  try { return fs.statSync(p).isDirectory(); } catch { return false; }
}

function findSassPairs() {
  if (!isDir(ADDONS_DIR)) return [];

  const addons = fs.readdirSync(ADDONS_DIR)
    .map((name) => path.join(ADDONS_DIR, name))
    .filter(isDir);

  const pairs = [];

  for (const addonPath of addons) {
    const addonName = path.basename(addonPath);

    // Convention: addons/<app>/static/<app>/scss -> css
    const scssDir = path.join(addonPath, "static", addonName, "scss");
    const cssDir  = path.join(addonPath, "static", addonName, "css");

    if (isDir(scssDir)) {
      pairs.push(`${scssDir}:${cssDir}`);
    }
  }
  return pairs;
}

const args = process.argv.slice(2); // pass through flags like --watch, --style=compressed
const pairs = findSassPairs();

if (pairs.length === 0) {
  console.error("No SCSS directories found under addons/<app>/static/<app>/scss");
  process.exit(1);
}

const sassArgs = [
  ...args,
  "--load-path=node_modules",
  ...pairs,
];

const child = spawn(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["sass", ...sassArgs],
  { stdio: "inherit" }
);

child.on("exit", (code) => process.exit(code ?? 1));
