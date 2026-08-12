#!/usr/bin/env node
"use strict";

// src/hooks/block-destructive.ts
function deny(reason) {
  const output = {
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: reason
    }
  };
  process.stdout.write(JSON.stringify(output) + "\n");
  process.exit(0);
}
function allow() {
  process.exit(0);
}
function main() {
  let input = "";
  process.stdin.setEncoding("utf-8");
  const timeoutId = setTimeout(() => {
    process.stdin.destroy();
    allow();
  }, 5e3);
  process.stdin.on("data", (chunk) => {
    input += chunk;
  });
  process.stdin.on("end", () => {
    clearTimeout(timeoutId);
    try {
      const hookInput = JSON.parse(input);
      const command = hookInput.tool_input?.command || "";
      if (!command) {
        allow();
        return;
      }
      if (/rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|(-[a-zA-Z]*\s+)*)(\/|~|\$HOME|\.\.)/.test(command)) {
        deny(
          "[Versus] Blocked destructive rm command targeting root, home, or parent directory. If intentional, run manually in a separate terminal."
        );
        return;
      }
      if (/DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\S+\s*;?\s*$/i.test(command)) {
        deny(
          "[Versus] Blocked destructive database command (DROP/TRUNCATE/DELETE without WHERE). If intentional, run manually in a separate terminal."
        );
        return;
      }
      if (/git\s+push\s+.*--force|git\s+push\s+-f\b|git\s+reset\s+--hard\s+(HEAD~|origin)/i.test(command)) {
        deny(
          "[Versus] Blocked force push or hard reset. If intentional, run manually in a separate terminal."
        );
        return;
      }
      if (/(cat|less|head|tail|more|source|grep|sed|awk|bat)\s+\.env\b|echo.*\$\(.*\.env/.test(command)) {
        deny(
          "[Versus] Blocked .env file access. Credentials should not be read by the agent. If needed, run manually in a separate terminal."
        );
        return;
      }
      allow();
    } catch {
      allow();
    }
  });
}
main();
