import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import * as ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourcePath = path.join(root, "app", "lib", "jdCriteriaFallback.ts");
const source = await fs.readFile(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const helper = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`,
);

// Keep the test runner independent from a browser, Vite and real services.
const successResponse = (criteria = [{ id: "criterion-1" }]) => ({
  success: true,
  data: { criteria },
  warnings: ["existing warning"],
});

function runWithLogs(remoteRequest, localRequest) {
  const logs = [];
  return helper.withCriteriaFallback(remoteRequest, localRequest, {
    fallbackWarning:
      "RunPod criteria service was unavailable; local rule-based criteria were used.",
    logger: (message, details) => logs.push({ message, details }),
  }).then((result) => ({ result, logs }));
}

test("RunPod configured and successful does not call local fallback", async () => {
  let localCalls = 0;
  const { result, logs } = await runWithLogs(
    async () => successResponse(),
    async () => {
      localCalls += 1;
      return successResponse();
    },
  );

  assert.equal(result.success, true);
  assert.equal(localCalls, 0);
  assert.deepEqual(logs.map(({ message }) => message), [
    "RunPod request attempted",
  ]);
});

test("missing RunPod configuration falls back locally", async () => {
  const { result, logs } = await runWithLogs(
    async () => {
      throw new Error("RunPod criteria service is not configured");
    },
    async () => successResponse(),
  );

  assert.equal(result.success, true);
  assert.equal(result.warnings[0],
    "RunPod criteria service was unavailable; local rule-based criteria were used.",
  );
  assert.deepEqual(logs.map(({ message }) => message), [
    "RunPod request attempted",
    "RunPod failed",
    "local fallback used",
  ]);
});

test("RunPod error payload falls back even when the request resolves", async () => {
  const { result } = await runWithLogs(
    async () => ({
      success: false,
      error: "RunPod criteria service is not configured",
    }),
    async () => successResponse([{ id: "local-criterion" }]),
  );

  assert.equal(result.data.criteria[0].id, "local-criterion");
});

test("missing criteria data is treated as an unusable RunPod response", async () => {
  const { result } = await runWithLogs(
    async () => ({ success: true, data: {}, warnings: [] }),
    async () => successResponse([{ id: "local-criterion" }]),
  );

  assert.equal(result.data.criteria[0].id, "local-criterion");
});

test("both services failing returns a clear error", async () => {
  await assert.rejects(
    () => runWithLogs(
      async () => {
        throw new Error("RunPod request failed");
      },
      async () => {
        throw new Error("local parser unavailable");
      },
    ),
    /RunPod was unavailable and the local rule-based fallback failed: local parser unavailable/,
  );
});
