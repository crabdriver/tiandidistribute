import http from "http";
import { existsSync, readFileSync } from "fs";
import { homedir } from "os";
import { resolve } from "path";

function uniquePorts(items) {
  const seen = new Set();
  const ordered = [];
  for (const item of items) {
    const port = Number(item);
    if (!Number.isFinite(port) || port <= 0 || seen.has(port)) {
      continue;
    }
    seen.add(port);
    ordered.push(port);
  }
  return ordered;
}

export function readDevToolsPortFileCandidates(homeDir = homedir()) {
  const candidates = [
    resolve(homeDir, "Library/Application Support/Google/Chrome/DevToolsActivePort"),
    resolve(homeDir, ".config/google-chrome/DevToolsActivePort"),
  ];

  const parsed = [];
  for (const path of candidates) {
    if (!existsSync(path)) {
      continue;
    }
    const [port, browserPath] = readFileSync(path, "utf8").trim().split("\n");
    parsed.push({ port: Number(port), browserPath: browserPath || "" });
  }
  return parsed;
}

function requestJsonVersion(port) {
  return new Promise((resolvePromise) => {
    const req = http.get(
      {
        hostname: "127.0.0.1",
        port,
        path: "/json/version",
        timeout: 1500,
      },
      (res) => {
        let raw = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          raw += chunk;
        });
        res.on("end", () => {
          if (res.statusCode !== 200) {
            resolvePromise(null);
            return;
          }
          try {
            resolvePromise(JSON.parse(raw));
          } catch {
            resolvePromise(null);
          }
        });
      }
    );
    req.on("error", () => resolvePromise(null));
    req.on("timeout", () => {
      req.destroy();
      resolvePromise(null);
    });
  });
}

export async function resolveBrowserWsUrl({
  env = process.env,
  portFileCandidates = readDevToolsPortFileCandidates(),
  requestJsonVersion: requestJsonVersionFn = requestJsonVersion,
} = {}) {
  if (env.LIVE_CDP_BROWSER_WS_URL) {
    return env.LIVE_CDP_BROWSER_WS_URL;
  }

  const preferredPorts = uniquePorts([
    env.LIVE_CDP_PORT,
    9222,
    ...portFileCandidates.map((item) => item.port),
  ]);

  for (const port of preferredPorts) {
    const info = await requestJsonVersionFn(port);
    if (info?.webSocketDebuggerUrl) {
      return info.webSocketDebuggerUrl;
    }
  }

  const fallback = portFileCandidates.find((item) => item.port && item.browserPath);
  if (fallback) {
    return `ws://127.0.0.1:${fallback.port}${fallback.browserPath}`;
  }

  throw new Error(
    "Could not find DevToolsActivePort. Enable Chrome remote debugging in chrome://inspect/#remote-debugging"
  );
}
