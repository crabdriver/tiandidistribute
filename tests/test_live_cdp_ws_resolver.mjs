import test from "node:test";
import assert from "node:assert/strict";

import { resolveBrowserConnection, resolveBrowserWsUrl } from "../live_cdp_ws_resolver.mjs";

test("prefers managed browser debug port before other CDP ports", async () => {
  const calls = [];
  const result = await resolveBrowserConnection({
    env: {
      ORDO_BROWSER_SESSION_DEBUG_PORT: "9333",
      LIVE_CDP_PORT: "9555",
    },
    portFileCandidates: [],
    requestJsonVersion: async (port) => {
      calls.push(port);
      if (port === 9333) {
        return { webSocketDebuggerUrl: "ws://127.0.0.1:9333/devtools/browser/managed" };
      }
      return null;
    },
  });

  assert.equal(result.source, "managed_browser_port");
  assert.equal(result.webSocketDebuggerUrl, "ws://127.0.0.1:9333/devtools/browser/managed");
  assert.deepEqual(calls, [9333]);
});

test("falls back to DevToolsActivePort candidate metadata when needed", async () => {
  const result = await resolveBrowserConnection({
    env: {},
    portFileCandidates: [
      {
        port: 9666,
        browserPath: "/devtools/browser/from-port-file",
        source: "managed_browser_port_file",
        detail: "当前 CDP 连接来源：Ordo 托管浏览器资料目录 /tmp/ordo-profile",
      },
    ],
    requestJsonVersion: async () => null,
  });

  assert.equal(result.source, "managed_browser_port_file");
  assert.equal(result.port, 9666);
  assert.equal(result.webSocketDebuggerUrl, "ws://127.0.0.1:9666/devtools/browser/from-port-file");
});

test("resolveBrowserWsUrl prefers a reachable debugging endpoint over stale port file data", async () => {
  const wsUrl = await resolveBrowserWsUrl({
    env: {},
    portFileCandidates: [
      { port: 63689, browserPath: "/devtools/browser/stale" },
      { port: 9222, browserPath: "/devtools/browser/fresh" },
    ],
    requestJsonVersion: async (port) => {
      if (port === 9222) {
        return { webSocketDebuggerUrl: "ws://127.0.0.1:9222/devtools/browser/live" };
      }
      return null;
    },
  });

  assert.equal(wsUrl, "ws://127.0.0.1:9222/devtools/browser/live");
});

test("resolveBrowserWsUrl returns explicit env websocket url first", async () => {
  const wsUrl = await resolveBrowserWsUrl({
    env: { LIVE_CDP_BROWSER_WS_URL: "ws://127.0.0.1:9999/devtools/browser/direct" },
    portFileCandidates: [],
    requestJsonVersion: async () => null,
  });

  assert.equal(wsUrl, "ws://127.0.0.1:9999/devtools/browser/direct");
});
