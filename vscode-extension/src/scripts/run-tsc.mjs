import { existsSync } from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const candidates = [
  path.resolve(process.cwd(), "node_modules/typescript/bin/tsc"),
  path.resolve(process.cwd(), "../frontend/node_modules/typescript/bin/tsc"),
];

const compiler = candidates.find((candidate) => existsSync(candidate));

if (!compiler) {
  console.error("TypeScript compiler not found. Run `npm install` in vscode-extension or frontend.");
  process.exit(1);
}

const child = spawn(process.execPath, [compiler, ...process.argv.slice(2)], {
  stdio: "inherit",
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
