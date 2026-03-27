import test from "node:test";
import assert from "node:assert/strict";

import { resolveBrowserWsUrl } from "../live_cdp_ws_resolver.mjs";

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
