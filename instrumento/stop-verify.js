#!/usr/bin/env node
"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// src/state/engine.ts
var fs = __toESM(require("fs"));
var path = __toESM(require("path"));
var import_crypto = require("crypto");

// src/state/types.ts
function specEntryValue(e) {
  return typeof e === "string" ? e : e.value;
}
function createDefaultState(name, description) {
  return {
    agent: "claude",
    projectName: name,
    projectDescription: description,
    projectSpec: { stack: [], outOfScope: [], patterns: [], constraints: [] },
    currentPhase: 0,
    currentIteration: 1,
    phase0Score: null,
    phase0Breakdown: null,
    decisions: [],
    activatedLenses: [],
    stateVersion: 1,
    exitCriteria: [],
    safeguards: [
      { id: "S0", status: "ok" },
      { id: "S1", status: "ok" },
      { id: "S2", status: "ok" },
      { id: "S3", status: "ok" },
      { id: "S4", status: "ok" },
      { id: "S5", status: "ok" },
      { id: "S6", status: "ok" },
      { id: "S7", status: "ok" }
    ],
    loopCounter: { pattern: "", count: 0, firstSeen: "", lastSeen: "" },
    createdAt: (/* @__PURE__ */ new Date()).toISOString(),
    updatedAt: (/* @__PURE__ */ new Date()).toISOString(),
    history: []
  };
}

// src/rules/phases.ts
var EXIT_CRITERIA = [
  // Phase 0
  { phase: 0, criterion: "score_90", description: "Score >= 90/100", required: true },
  { phase: 0, criterion: "user_confirmed", description: "User confirmed synthesis", required: true },
  { phase: 0, criterion: "ambiguities_zero", description: "Ambiguities = 0 (or accepted)", required: true },
  { phase: 0, criterion: "use_cases_complete", description: "Use cases complete", required: true },
  { phase: 0, criterion: "vocabulary_agreed", description: "Vocabulary agreed upon", required: true },
  { phase: 0, criterion: "out_of_scope_clear", description: "Out of scope clear", required: true },
  { phase: 0, criterion: "tech_feasibility", description: "Target platform tech feasibility VERIFIED: fundamental capabilities confirmed (not assumed). In porting projects: does the destination platform support essential mechanisms?", required: true },
  { phase: 0, criterion: "implementation_feasibility", description: "Components evaluated Tier 1/2/3. If complex Tier 3 \u2192 PoC before Phase 1", required: true },
  { phase: 0, criterion: "technical_scientific_research", description: "If specialized domain: complete technical AND scientific research (F.2) \u2014 papers, algorithms, parameters with source", required: false },
  { phase: 0, criterion: "specs_populated", description: "specs/ populated with technical and scientific references", required: true },
  // Phase 1
  { phase: 1, criterion: "patterns_defined", description: "Patterns/principles defined and confirmed", required: true },
  { phase: 1, criterion: "modules_responsibility", description: "Each module with clear responsibility", required: true },
  { phase: 1, criterion: "interfaces_defined", description: "Interfaces defined (signatures, I/O types)", required: true },
  { phase: 1, criterion: "dependencies_explicit", description: "Dependencies between modules explicit", required: true },
  { phase: 1, criterion: "assumptions_listed", description: "Assumptions listed", required: true },
  { phase: 1, criterion: "architecture_doc", description: "Architecture doc written to specs/technical/architecture.md, containing a MODULE TABLE (M-01 | module | responsibility | interface | depends-on) so the canonical module list is machine-readable \u2014 the same names Phase 2's matrix and Phase 5 reference", required: true, artifact: "technical/architecture.md", artifactRows: { pattern: "\\|\\s*M-\\d+\\s*\\|", count: 1, example: "M-01 | rate-limiter | enforce quota | allow(key) | store" } },
  { phase: 1, criterion: "tech_100_scope", description: "Tech supports 100% of scope, tech assumptions verified", required: true },
  { phase: 1, criterion: "modules_adherent_patterns", description: "Modules adherent to chosen patterns", required: true },
  // Phase 2
  { phase: 2, criterion: "activated_lenses_recorded", description: "Activated conditional lenses recorded via record_activated_lenses() \u2014 the structured tool, not free-text prose. Every one of the 12 conditional lenses must appear either as activated or as not-activated WITH a reason; names are validated against the canonical set, so no abbreviation or translation can enter; a fresh record is required for each iteration of the 2\u21943 loop", required: true, verify: "lenses-recorded" },
  { phase: 2, criterion: "lenses_applied", description: "All 7 universal lenses + all activated conditional lenses applied to each module (no lens skipped \u2014 absence of findings is a valid result)", required: true },
  { phase: 2, criterion: "coverage_matrix", description: "Coverage findings table written to specs/design/coverage-matrix.md \u2014 ONE ROW PER FINDING (id | module | lens | severity | description), each with a unique in-project id and 'duplica: <id>' when it is the same defect another lens found. Per-finding ids (not a severity-per-cell grid) are what let overlap be distinguished from orthogonality", required: true, artifact: "design/coverage-matrix.md", artifactRows: { pattern: "\\|\\s*(?!M-)[A-Za-z]{1,4}-\\d+\\s*\\|", count: 1, example: "P-01 | auth | Security | \u{1F534} | sql-injection in login" } },
  { phase: 2, criterion: "criticals_identified", description: "Critical findings identified and classified", required: true },
  { phase: 2, criterion: "concentration_analyzed", description: "Concentration analysis performed (by module and by lens)", required: true },
  // Phase 3
  { phase: 3, criterion: "criticals_addressed", description: "All critical findings addressed", required: true },
  { phase: 3, criterion: "important_decided", description: "All important findings with decision", required: true },
  { phase: 3, criterion: "scope_preserved", description: "Phase 0 scope preserved (anti-scope-creep)", required: true },
  { phase: 3, criterion: "architecture_simplified", description: "Architecture simpler than previous", required: true },
  // Phase 4
  { phase: 4, criterion: "exit_criteria_p2p3", description: "Exit criteria Phases 2-3 verified", required: true },
  { phase: 4, criterion: "safeguards_s1_s5", description: "Safeguards S1-S5 met", required: true },
  // Phase 5
  { phase: 5, criterion: "all_modules", description: "All modules implemented", required: true },
  { phase: 5, criterion: "specs_consulted", description: "specs/ consulted before each module", required: true },
  { phase: 5, criterion: "s6_applied", description: "S6 applied (Tier 1/2/3 per module)", required: true },
  { phase: 5, criterion: "ui_runnable", description: "Smoke test: user runs P0 end-to-end", required: true },
  // Phase 6
  { phase: 6, criterion: "tests_passing", description: "100% tests passing \u2014 the test-outcome hook must have witnessed a green run in Phase 6 (S4: execute and verify, do not assume)", required: true, verify: "test-pass" },
  { phase: 6, criterion: "manual_testing", description: "Manual exploratory testing performed", required: true },
  { phase: 6, criterion: "edge_cases", description: "Edge cases tested", required: true },
  // Phase 7
  { phase: 7, criterion: "specs_updated", description: "specs/ updated with results", required: true },
  { phase: 7, criterion: "lessons_documented", description: "Lessons learned written to specs/references/lessons.md \u2014 the persisted record that feeds the next cycle", required: true, artifact: "references/lessons.md" },
  { phase: 7, criterion: "human_feedback", description: "Human feedback collected", required: true }
];
function getExitCriteriaForPhase(phase) {
  return EXIT_CRITERIA.filter((c) => c.phase === phase);
}
function isValidTransition(from, to) {
  if (to === from + 1) return true;
  if (from === 3 && to === 2) return true;
  if (from === 2 && to === 3) return true;
  return false;
}

// src/rules/lenses.ts
var UNIVERSAL_LENS_DEFS = [
  { name: "Assumptions", question: "What does this design assume as true without declaring?", failureClass: "Failures from hidden assumptions" },
  { name: "Architectural", question: "Can each module be replaced, removed, or tested in isolation?", failureClass: "Hidden coupling, circular dependencies, SRP violation" },
  { name: "Implementability", question: "Can I code this module in a single session with available context?", failureClass: "Incomplete specs, insufficient granularity" },
  { name: "Scientific", question: "Does each value/formula/algorithm have a verifiable bibliographic reference?", failureClass: "Invented parameters, plausibility-based logic" },
  { name: "Security", question: "How would an attacker exploit this with minimal effort?", failureClass: "Unanalyzed attack surface" },
  { name: "Performance", question: "Where are the bottlenecks? Asymptotic behavior?", failureClass: "Hidden bottlenecks, degradation at scale" },
  { name: "Regulatory", question: "Does each normative requirement have traceability to a module?", failureClass: "Non-compliance with applicable standards" }
];
var CONDITIONAL_LENS_DEFS = [
  { name: "Resilience", question: "What happens when an external dependency fails, responds slowly, or returns unexpected data?", failureClass: "Cascading failures, retry storms, partial outages", trigger: "External dependencies (APIs, DBs, queues, third-party services)" },
  { name: "UI/UX", question: "Can the user complete their task without frustration, confusion, or error?", failureClass: "Confusing flows, dead-end states, missing feedback, accessibility failures", trigger: "Any surface a PERSON operates \u2014 including a CLI or operational tooling, not only graphical end-user interfaces" },
  { name: "Migration / Coexistence", question: "What breaks during the transition from old to new? Is there a rollback path?", failureClass: "Data loss in migration, functional regression vs. legacy, impossible rollback", trigger: "Replacing or modifying existing production system" },
  { name: "Sustainability / Proportionality", question: "Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale?", failureClass: "GPU where CPU suffices, heavy model for simple task, infinite data retention", trigger: "The system decides, allocates, or consumes a resource whose cost grows with use \u2014 e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples" },
  { name: "Ethical / Human Impact", question: "Who is potentially harmed? Are there audit, correction, and transparency mechanisms?", failureClass: "Algorithmic bias, digital exclusion, automated decisions without human recourse", trigger: "Automated decisions about people (scoring, classification, moderation)" },
  { name: "Process / Workflow", question: "Are processes, state transitions, actor responsibilities, and exception paths complete?", failureClass: "Orphaned states, ambiguous handoffs, missing actors, happy-path bias", trigger: "Multi-actor flows, state machines, or business processes" },
  { name: "Governance / Accountability", question: "Is every action attributable? Does every data entity have a defined owner?", failureClass: "No data ownership, no accountability, shadow data flows", trigger: "The system records or decides something someone will later need to audit, attribute, or answer for \u2014 data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts)" },
  { name: "Observability / Operability", question: "Can degradation be detected and incidents diagnosed in production without code changes?", failureClass: "Opaque systems where nobody can figure out why it failed", trigger: "Production systems with operational requirements" },
  { name: "Control Engineering", question: "Where does the system generate an error signal and correct it? Risk of oscillation or state drift?", failureClass: "Systems that react to events but don't regulate state \u2014 oscillation, drift, runaway feedback", trigger: "State synchronization, runtime configuration affecting behavior, self-correcting or feedback-driven systems" },
  { name: "Game Theory", question: "Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection?", failureClass: "Architectures that work under cooperation assumptions but collapse under adversarial or strategic behavior", trigger: "Multiple independent actors, public API, external integrations, marketplace or platform design" },
  { name: "Linguistics / Grammar", question: "Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors?", failureClass: "Protocol ambiguity \u2014 two correct implementations that are mutually incompatible", trigger: "Inter-component communication, protocol definitions, message formats, interface contracts between independent teams" },
  { name: "Mechanical Engineering", question: "Where are the tolerances? Does the system tolerate variation or only work at exact specification?", failureClass: "Rigid coupling disguised as tolerance \u2014 failure from small deviations in dependency versions, environment, or load", trigger: "Module maintenance, system evolution, long-lived systems with technical debt accumulation" }
];
var UNIVERSAL_LENSES = UNIVERSAL_LENS_DEFS.map((l) => l.name);
var CONDITIONAL_LENSES = CONDITIONAL_LENS_DEFS.map((l) => l.name);
var ALL_LENSES = [...UNIVERSAL_LENSES, ...CONDITIONAL_LENSES];
function canonicalLens(raw) {
  const norm = (s) => s.trim().toLowerCase().replace(/\s*\/\s*/g, "/").replace(/\s+/g, " ");
  const target = norm(raw);
  return ALL_LENSES.find((l) => norm(l) === target) ?? null;
}

// src/rules/safeguards.ts
var LOOP_FAILURE_THRESHOLD = 3;
var DIAGNOSIS_CATEGORIES = ["diagnosis", "bugfix", "root-cause"];
var SAFEGUARD_DEFINITIONS = [
  {
    id: "S0",
    name: "Problem Convergence",
    description: "Never advance to Phase 1 without score >= 90/100. Wrong problem costs 100x.",
    applicablePhases: [0]
  },
  {
    id: "S1",
    name: "Anti-Bug",
    description: "Simplification never introduces bugs. Features maintained after each Phase 3.",
    applicablePhases: [3]
  },
  {
    id: "S2",
    name: "Stopping Criterion",
    description: "Stopping criterion belongs to the USER, not the AI.",
    applicablePhases: [0, 1, 2, 3, 4, 5, 6, 7]
  },
  {
    id: "S3",
    name: "Premature Convergence Cost",
    description: "Stopping early = -400% to -600% ROI. Prefer iterating when in doubt.",
    applicablePhases: [0, 2, 3]
  },
  {
    id: "S4",
    name: "Explicit Verification (mandatory human-AV)",
    description: "Human-AV is irreplaceable at each gate. Automated tests verify formalizable properties. Semantic adequacy, usability, and domain correctness REQUIRE human judgment. P0: human validates synthesis. P2: human arbitrated trade-offs. P4: human confirms convergence. P6: NEVER assume tests passed \u2014 execute and verify + mandatory manual exploratory testing.",
    applicablePhases: [0, 2, 4, 6]
  },
  {
    id: "S5",
    name: "Scope Preservation",
    description: "Phase 2-3 operates WITHIN Phase 0 scope. Sub-rules: 5.1 Scope belongs to the user \u2014 Phase 2-3 suggests, never decides changes. 5.2 If not requested, don't add. If useful, document as v2.0 suggestion. 5.3 Detector: 'If the user compared V(N) with Phase 0, would they say this isn't what I asked for?' If yes \u2192 scope violated.",
    applicablePhases: [2, 3]
  },
  {
    id: "S6",
    name: "Don't Reimplement What Already Exists",
    description: `Tier 1: mature lib \u2192 USE IT. Tier 2: algorithm with ref \u2192 PORT literally (same structure, same names, test against same inputs). Tier 3: neither of the above. If complex domain \u2192 PoC (~2h max). Immediate STOP if: creating heuristics for problem with known solution, debugging complex logic from scratch, trial-and-error on something deterministic, or >2 iterations on the same module. Checklist per module: mature lib? \u2192 if not, why? \u2192 documented algorithm? \u2192 portable ref? \u2192 decision. Loop detection: ${LOOP_FAILURE_THRESHOLD} consecutive FAILED test runs with no diagnosis recorded between them blocks the next run. A passing run never counts (S4 verification is never blockable) and record_decision(category='diagnosis') clears the counter. Debugging with a named cause per round is the normal cycle; failing repeatedly without naming a cause is the blind loop.`,
    applicablePhases: [5, 6]
  },
  {
    id: "S7",
    name: "Sequence Discipline",
    description: "After each file: mark completed, identify next, announce progress, start immediately.",
    applicablePhases: [5]
  }
];
function getSafeguardDefinition(id) {
  return SAFEGUARD_DEFINITIONS.find((s) => s.id === id);
}
function getSafeguardsForPhase(phase) {
  return SAFEGUARD_DEFINITIONS.filter((s) => s.applicablePhases.includes(phase));
}
function validateSafeguard(id, state) {
  const def = getSafeguardDefinition(id);
  if (!def) {
    return { id, status: "ok", details: `Safeguard ${id} not found.` };
  }
  switch (id) {
    case "S0":
      return validateS0(state);
    case "S1":
      return validateS1(state);
    case "S5":
      return validateS5(state);
    case "S6":
      return validateS6(state);
    case "S7":
      return validateS7(state);
    default:
      return {
        id,
        status: "ok",
        details: `${def.name}: behavioral check \u2014 requires agent attention. ${def.description}`
      };
  }
}
function validateS0(state) {
  if (state.currentPhase === 0) {
    return { id: "S0", status: "ok", details: "Still in Phase 0. Current score: " + (state.phase0Score ?? "not evaluated") };
  }
  if (state.phase0Score === null || state.phase0Score < 90) {
    return {
      id: "S0",
      status: "violated",
      details: `Phase 0 score ${state.phase0Score ?? "null"} < 90. Should not have advanced.`
    };
  }
  return { id: "S0", status: "ok", details: `Phase 0 score ${state.phase0Score}/100. OK.` };
}
function validateS1(state) {
  if (state.currentPhase !== 3) {
    return { id: "S1", status: "ok", details: "Not in Phase 3." };
  }
  return {
    id: "S1",
    status: "warning",
    details: "Phase 3 active: verify that simplification did not introduce bugs. Features must be maintained."
  };
}
function validateS5(state) {
  if (state.currentPhase !== 2 && state.currentPhase !== 3) {
    return { id: "S5", status: "ok", details: "Not in Phase 2-3." };
  }
  return {
    id: "S5",
    status: "warning",
    details: "Phase 2-3 active: Phase 0 scope must be preserved. Don't cut requirements, don't add features."
  };
}
function validateS6(state) {
  if (state.currentPhase < 5) {
    return { id: "S6", status: "ok", details: "Not in implementation." };
  }
  const undiagnosedFailures = state.loopCounter?.count ?? 0;
  if (undiagnosedFailures >= LOOP_FAILURE_THRESHOLD) {
    return {
      id: "S6",
      status: "violated",
      details: `${undiagnosedFailures} consecutive failed runs of "${state.loopCounter.pattern}" with no diagnosis recorded. Test runs are blocked. Name the root cause via record_decision(category='diagnosis') to clear it, or go Tier 2 (find a reference implementation) if you cannot name one.`
    };
  }
  return {
    id: "S6",
    status: "warning",
    details: `Implementation active: verify Tier 1/2/3 per module. STOP if creating heuristics for problems with known solutions. Undiagnosed consecutive test failures: ${undiagnosedFailures}/${LOOP_FAILURE_THRESHOLD}.`
  };
}
function validateS7(state) {
  if (state.currentPhase !== 5) {
    return { id: "S7", status: "ok", details: "Not in Phase 5." };
  }
  return {
    id: "S7",
    status: "warning",
    details: "Phase 5 active: after each file, mark completed and announce progress. Don't start tangential discussions."
  };
}

// src/state/engine.ts
function validatePhaseTransition(from, to, state, exitCriteriaMet) {
  const result = {
    valid: true,
    missingCriteria: [],
    safeguardViolations: []
  };
  if (!isValidTransition(from, to)) {
    result.valid = false;
    result.missingCriteria.push(
      `Transition from Phase ${from} to Phase ${to} is not allowed. Valid transitions: sequential or loop 2\u21943.`
    );
    return result;
  }
  if (to > from) {
    const criteria = getExitCriteriaForPhase(from);
    for (const criterion of criteria) {
      if (criterion.required && !exitCriteriaMet.get(criterion.criterion)) {
        result.valid = false;
        result.missingCriteria.push(
          `[Phase ${from}] ${criterion.criterion}: ${criterion.description}`
        );
      }
    }
  }
  if (from === 0 && to === 1) {
    if (state.phase0Score === null || state.phase0Score < 90) {
      result.valid = false;
      result.missingCriteria.push(
        `Phase 0 score = ${state.phase0Score ?? "null"}. Required >= 90.`
      );
    }
  }
  const safeguards = getSafeguardsForPhase(from);
  for (const safeguard of safeguards) {
    const check = validateSafeguard(safeguard.id, state);
    if (check.status === "violated") {
      result.valid = false;
      result.safeguardViolations.push(`${safeguard.id}: ${check.details}`);
    }
  }
  return result;
}
var StateEngine = class {
  state = null;
  statePath;
  specsPath;
  workspacePath;
  constructor(workspacePath) {
    this.workspacePath = workspacePath;
    this.statePath = path.join(workspacePath, ".versus", "state.json");
    this.specsPath = path.join(workspacePath, "specs");
  }
  getWorkspace() {
    return this.workspacePath;
  }
  // --- Lifecycle ---
  load() {
    try {
      if (fs.existsSync(this.statePath)) {
        const raw = fs.readFileSync(this.statePath, "utf-8");
        this.state = JSON.parse(raw);
        return this.state;
      }
    } catch (err) {
    }
    return null;
  }
  save() {
    if (!this.state) return;
    this.state.updatedAt = (/* @__PURE__ */ new Date()).toISOString();
    const dir = path.dirname(this.statePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(this.statePath, JSON.stringify(this.state, null, 2), "utf-8");
  }
  // --- Project ---
  initProject(name, description) {
    this.state = createDefaultState(name, description);
    this.save();
    return this.state;
  }
  // --- Gateway Guard ---
  touchPhaseStateCheck() {
    if (!this.state) return;
    this.state.lastPhaseStateCheck = (/* @__PURE__ */ new Date()).toISOString();
    this.save();
  }
  isContextStale(thresholdMinutes = 30) {
    if (!this.state) return true;
    if (!this.state.lastPhaseStateCheck) return true;
    const last = new Date(this.state.lastPhaseStateCheck).getTime();
    return Date.now() - last > thresholdMinutes * 60 * 1e3;
  }
  // --- Query ---
  getPhaseState() {
    if (!this.state) this.load();
    return this.state;
  }
  getDecisions(phase) {
    if (!this.state) return [];
    if (phase !== void 0) {
      return this.state.decisions.filter((d) => d.phase === phase);
    }
    return this.state.decisions;
  }
  getExitCriteriaState(phase) {
    if (!this.state) return [];
    return this.state.exitCriteria.filter((c) => c.phase === phase);
  }
  getExitCriteriaWithDefs(phase) {
    const defs = getExitCriteriaForPhase(phase);
    const states = this.getExitCriteriaState(phase);
    return defs.map((def) => {
      const state = states.find((s) => s.criterion === def.criterion);
      return {
        criterion: def.criterion,
        description: def.description,
        met: state?.met ?? false,
        details: state?.details
      };
    });
  }
  // --- Transitions ---
  /**
   * True if a specs/ artifact exists and has non-trivial content. This is the
   * forensic bar: not "is it good" (the oracle — unmechanizable) but "does a
   * persisted, inspectable record exist" — so a stamped gate leaves a trace to
   * audit after a failure instead of vanishing in the chat. relPath is relative
   * to specs/.
   */
  artifactPresent(relPath) {
    try {
      const full = path.join(this.specsPath, relPath);
      if (!fs.existsSync(full)) return false;
      const content = fs.readFileSync(full, "utf-8").replace(/\s/g, "");
      return content.length >= 80;
    } catch {
      return false;
    }
  }
  /** Module names in the 2nd column of table rows whose 1st cell matches idPattern.
   *  Used to extract the module set from architecture.md (M-\d+ rows) and from the
   *  coverage matrix (finding-id rows). Normalized (trim + lowercase) for comparison. */
  tableColumn2(relPath, idPattern) {
    const out = /* @__PURE__ */ new Set();
    try {
      const full = path.join(this.specsPath, relPath);
      if (!fs.existsSync(full)) return out;
      const text = fs.readFileSync(full, "utf-8");
      const re = new RegExp(`\\|\\s*(?:${idPattern})\\s*\\|\\s*([^|]+?)\\s*\\|`, "gm");
      let m;
      while ((m = re.exec(text)) !== null) {
        const v = m[1].trim().toLowerCase();
        if (v) out.add(v);
      }
    } catch {
    }
    return out;
  }
  /**
   * Drift between the coverage matrix and the architecture: every module a finding
   * cites must appear in architecture.md's module table, in SOME version. The union
   * of all `## V(N)` module tables tolerates a module removed in a later iteration
   * (its earlier findings are legitimate) while catching a name that was never a
   * module — which breaks the matrix's per-module traceability silently. Skips when
   * either artifact is absent/empty (other gates handle that). Case-insensitive.
   */
  moduleTraceabilityErrors() {
    const arch = this.tableColumn2("technical/architecture.md", "M-\\d+");
    const matrix = this.tableColumn2("design/coverage-matrix.md", "(?!M-)[A-Za-z]{1,4}-\\d+");
    if (arch.size === 0 || matrix.size === 0) return [];
    const drift = [...matrix].filter((mod) => !arch.has(mod));
    if (drift.length === 0) return [];
    return [
      `[Phase 2] coverage_matrix cites module(s) absent from every version of the architecture table: ${drift.join(", ")}. Each module in a finding row must appear in specs/technical/architecture.md's module table (any \`## V(N)\` version). Either the name drifted \u2014 fix it to the Phase-1 module name \u2014 or the architecture is missing the module. Left unfixed, those findings point at modules no artifact records, and per-module traceability breaks after the session.`
    ];
  }
  /**
   * The current critique iteration: how many times the run has ENTERED Phase 2.
   * `currentIteration` cannot serve this — it resets to 1 on every phase change,
   * INCLUDING the 3→2 loop-back, so it does not track the critique round. Counting
   * transitions into Phase 2 (the initial 1→2 plus each 3→2 loop) does, and it is
   * the number the matrix's `## Iteração N` headers are meant to mirror. Minimum 1
   * so a declaration made before any transition (tests) still lands somewhere.
   */
  critiqueIteration() {
    const entries = (this.state?.history ?? []).filter((h) => h.to === 2).length;
    return Math.max(1, entries);
  }
  /** Current architecture version = number of `## V(N)` sections in architecture.md,
   *  or 1 if none/absent. Stamped on a lens declaration as `againstVersion` so the
   *  analysis can see which design the critique ran against. */
  currentArchitectureVersion() {
    try {
      const full = path.join(this.specsPath, "technical/architecture.md");
      if (!fs.existsSync(full)) return 1;
      const text = fs.readFileSync(full, "utf-8");
      const n = (text.match(/^#{1,6}\s*V\s*\(\s*\d+\s*\)/gmi) || []).length;
      return n > 0 ? n : 1;
    } catch {
      return 1;
    }
  }
  /** Finding rows of the coverage matrix, each tagged with the iteration of the
   *  `## Iteração N` section it sits under (null before the first header). The lens
   *  is the 3rd cell, severity the 4th — the row format is frozen
   *  (id | module | lens | severity | desc). */
  matrixFindings() {
    const out = [];
    try {
      const full = path.join(this.specsPath, "design/coverage-matrix.md");
      if (!fs.existsSync(full)) return out;
      const text = fs.readFileSync(full, "utf-8");
      const idRe = /^(?!M-)[A-Za-z]{1,4}-\d+$/;
      const headerRe = /^#{1,6}\s*(?:Itera[cç][ãa]o|Iteration)\s+(\d+)/i;
      let currentIter = null;
      for (const line of text.split(/\r?\n/)) {
        const h = line.match(headerRe);
        if (h) {
          currentIter = parseInt(h[1], 10);
          continue;
        }
        if (!line.includes("|")) continue;
        const cells = line.split("|").map((c) => c.trim());
        if (cells.length && cells[0] === "") cells.shift();
        if (cells.length && cells[cells.length - 1] === "") cells.pop();
        if (cells.length < 3) continue;
        if (!idRe.test(cells[0])) continue;
        out.push({ id: cells[0], lens: cells[2], severity: cells[3] ?? "", iteration: currentIter });
      }
    } catch {
    }
    return out;
  }
  /**
   * Errors in a finding row of the coverage matrix (2→3 gate). Three layers, all
   * form (never quality — whether a finding is real stays a human judgment):
   *   LENS 2.1 — every finding's lens must be one of the 19 canonical names, or the
   *         literal NENHUMA (the declared channel for a finding that fit no lens).
   *         `Sustainability` (a truncation) is rejected; the canonical name accepted.
   *   LENS 2.2 — a CONDITIONAL lens must have been DECLARED for that finding's
   *         iteration. Universals always run, so they never fail 2.2. Matched against
   *         the declaration WITH THE SAME iteration number — never the current one nor
   *         the union, the trap the v0.13.0 module gate proved costly: a lens set
   *         legitimately evolves across the loop (MEC entered in iteration 2 in the
   *         pilot). When the iteration cannot be resolved, the check degrades to the
   *         UNION of all declared sets — permissive, never over-blocking. Skips 2.2
   *         when nothing is declared yet.
   *   SEVERITY — the 4th cell must carry exactly one of 🔴 / 🟡 / 🟢. The analysis
   *         counts criticals vs important on this column; "high", "P1" or an empty
   *         cell would be miscounted. Tolerant of decoration ("🔴 Critical" passes),
   *         strict on the signal (zero or two severities blocks). All 853 findings in
   *         the pilot corpus already use exactly these three glyphs.
   */
  findingRowErrors() {
    const findings = this.matrixFindings();
    if (findings.length === 0) return [];
    const acts = this.state?.activatedLenses ?? [];
    const union = /* @__PURE__ */ new Set();
    const byIter = /* @__PURE__ */ new Map();
    for (const a of acts) {
      for (const c of a.conditional) union.add(c);
      byIter.set(a.iteration, new Set(a.conditional));
    }
    const universals = new Set(UNIVERSAL_LENSES);
    const SEVERITIES = ["\u{1F534}", "\u{1F7E1}", "\u{1F7E2}"];
    const errs = [];
    for (const f of findings) {
      const sev = SEVERITIES.filter((s) => f.severity.includes(s));
      if (sev.length !== 1) {
        errs.push(
          `[Phase 2] coverage_matrix row ${f.id}: severity "${f.severity || "(empty)"}" must be exactly one of \u{1F534} (Critical) / \u{1F7E1} (Important) / \u{1F7E2} (Suggestion). The analysis counts criticals vs important on this column \u2014 a word, a code like "P1", or an empty cell cannot be counted.`
        );
      }
      if (/^nenhuma$/i.test(f.lens)) continue;
      const canon = canonicalLens(f.lens);
      if (!canon) {
        errs.push(
          `[Phase 2] coverage_matrix row ${f.id}: lens "${f.lens}" is not one of the 19 canonical lens names (nor NENHUMA). Use the EXACT canonical name \u2014 an abbreviation or a translation breaks cross-project analysis, which groups on this column.`
        );
        continue;
      }
      if (universals.has(canon)) continue;
      if (acts.length === 0) continue;
      const iterSet = f.iteration !== null ? byIter.get(f.iteration) : void 0;
      const declared = iterSet ?? union;
      if (!declared.has(canon)) {
        const scope = iterSet ? `iteration ${f.iteration}` : "any declared iteration";
        errs.push(
          `[Phase 2] coverage_matrix row ${f.id}: lens "${canon}" was not among the conditional lenses declared for ${scope} (declared: ${[...declared].join(", ") || "none"}). A finding may only use a lens activated for its own iteration \u2014 declare it for that round with record_activated_lenses, or fix the finding's lens.`
        );
      }
    }
    return errs;
  }
  /** How many lines of a specs/ artifact match `pattern`. Used for structural
   *  gates (e.g. per-finding rows in the coverage matrix). Form, not content. */
  countArtifactRows(relPath, pattern) {
    try {
      const full = path.join(this.specsPath, relPath);
      if (!fs.existsSync(full)) return 0;
      const text = fs.readFileSync(full, "utf-8");
      const re = new RegExp(pattern, "gm");
      return (text.match(re) || []).length;
    } catch {
      return 0;
    }
  }
  /** True if the test-outcome hook witnessed a passing run in `phase`. Gates
   *  tests_passing: the engine saw the green run, it was not merely asserted. */
  witnessedTestPass(phase) {
    const t = this.state?.lastTestOutcome;
    return !!t && t.outcome === "pass" && t.phase === phase;
  }
  /**
   * Records Phase 2 lens activation as structured state, stamped with the current
   * critique iteration and architecture version. Rejects any name outside the
   * canonical 12 conditionals and any lens left unaccounted for: silence about a
   * lens is exactly what the criterion exists to prevent — "I did not activate it"
   * and "I forgot it" must not look the same. Re-recording within the SAME iteration
   * replaces that iteration's entry (a correction); a new iteration appends, so the
   * per-round history the matrix gate reads is preserved across the 2↔3 loop.
   */
  recordActivatedLenses(conditional, notActivated) {
    if (!this.state) {
      return { ok: false, error: { message: "Project not initialized." } };
    }
    const asConditional = (raw) => {
      const c = canonicalLens(raw);
      return c && CONDITIONAL_LENSES.includes(c) ? c : null;
    };
    const outOfDomain = (raw) => canonicalLens(raw) ? `"${raw}" is a UNIVERSAL lens. Universals always run and are not passed here \u2014 this field records the CONDITIONAL set, and counting a universal among them corrupts it.` : `"${raw}" is not one of the 12 conditional lenses. Use the exact canonical name \u2014 abbreviations and translations break cross-project analysis, which groups on this value.`;
    const canon = [];
    for (const raw of conditional) {
      const c = asConditional(raw);
      if (!c) return { ok: false, error: { message: outOfDomain(raw) } };
      if (canon.includes(c)) {
        return { ok: false, error: { message: `Lens "${c}" is listed twice as activated. A duplicate inflates the activated count while passing the completeness check unnoticed.` } };
      }
      canon.push(c);
    }
    const no = [];
    for (const item of notActivated) {
      const c = asConditional(item.lens);
      if (!c) return { ok: false, error: { message: outOfDomain(item.lens) } };
      if (canon.includes(c)) {
        return { ok: false, error: { message: `Lens "${c}" appears as BOTH activated and not-activated. The record would contradict itself, and a later analysis has no way to tell which was meant.` } };
      }
      if (no.some((x) => x.lens === c)) {
        return { ok: false, error: { message: `Lens "${c}" is listed twice as not-activated.` } };
      }
      if (!item.reason || !item.reason.trim()) {
        return { ok: false, error: { message: `Lens "${c}" is marked not-activated without a reason. The justification is half the record: without it there is no way to tell a considered exclusion from an oversight.` } };
      }
      no.push({ lens: c, reason: item.reason.trim() });
    }
    const counted = /* @__PURE__ */ new Set([...canon, ...no.map((n) => n.lens)]);
    const missing = CONDITIONAL_LENSES.filter((l) => !counted.has(l));
    if (missing.length > 0) {
      return { ok: false, error: { message: `${missing.length} conditional lens(es) unaccounted for: ${missing.join(", ")}. Every one of the 12 must be either activated or explicitly not activated with a reason.` } };
    }
    const iteration = this.critiqueIteration();
    const activation = {
      universal: [...UNIVERSAL_LENSES],
      conditional: canon,
      notActivated: no,
      iteration,
      againstVersion: this.currentArchitectureVersion(),
      recordedAt: (/* @__PURE__ */ new Date()).toISOString()
    };
    if (!this.state.activatedLenses) this.state.activatedLenses = [];
    const existing = this.state.activatedLenses.findIndex((a) => a.iteration === iteration);
    if (existing >= 0) this.state.activatedLenses[existing] = activation;
    else this.state.activatedLenses.push(activation);
    this.save();
    return { ok: true, value: activation };
  }
  /** True if Phase 2 lens activation is on record for the CURRENT critique iteration.
   *  Checking the current iteration (not merely "any entry") is what forces a fresh
   *  declaration each round of the 2↔3 loop — a stale entry from iteration 1 must not
   *  satisfy the gate for iteration 2. Legacy free-text is honoured ONLY for projects
   *  created before this schema (no stateVersion); on new projects the structured
   *  record is mandatory, so the fallback cannot become an opt-out. */
  lensesRecorded() {
    const acts = this.state?.activatedLenses ?? [];
    if (acts.some((a) => a.iteration === this.critiqueIteration())) return true;
    if (this.state?.stateVersion !== void 0) return false;
    const marks = ["ACTIVATED LENSES", "LENTES ATIVADAS"];
    return (this.state?.decisions ?? []).some(
      (d) => marks.some((m) => d.content.toUpperCase().includes(m))
    );
  }
  /**
   * Messages for required criteria of `phase` whose persisted/witnessed evidence
   * is missing — empty means all evidence is present. Shared by advancePhase and
   * startNewCycle so a stamped criterion cannot open either gate without leaving
   * an inspectable trace. Does NOT judge quality (that is the oracle — human).
   */
  missingEvidence(phase) {
    const out = [];
    for (const def of getExitCriteriaForPhase(phase)) {
      if (!def.required) continue;
      if (def.artifact && !this.artifactPresent(def.artifact)) {
        out.push(
          `[Phase ${phase}] ${def.criterion}: required artifact specs/${def.artifact} is missing or empty. Write the structured artifact to disk \u2014 marking the criterion met is not enough; the record must survive the session and be inspectable later.`
        );
      } else if (def.artifact && def.artifactRows && this.countArtifactRows(def.artifact, def.artifactRows.pattern) < def.artifactRows.count) {
        const eg = def.artifactRows.example ? `, e.g. '${def.artifactRows.example}'` : "";
        out.push(
          `[Phase ${phase}] ${def.criterion}: specs/${def.artifact} exists but is not in the required structured form (needs at least ${def.artifactRows.count} table row(s) with an id${eg}). A prose or id-less file cannot be machine-read \u2014 each row needs its own id.`
        );
      }
      if (def.verify === "test-pass" && !this.witnessedTestPass(phase)) {
        out.push(
          `[Phase ${phase}] ${def.criterion}: the engine did not witness a passing test run in this phase. Run your test suite so the result is verified by the test-outcome hook (S4: never assume tests passed \u2014 execute and verify). Marking the criterion met is not enough.`
        );
      }
      if (def.verify === "lenses-recorded" && !this.lensesRecorded()) {
        out.push(
          `[Phase ${phase}] ${def.criterion}: lens activation is not on record for iteration ${this.critiqueIteration()}. Call record_activated_lenses(conditional, notActivated) \u2014 the structured tool \u2014 BEFORE advancing. Marking the criterion met is not enough: without the record, which lenses were applied cannot be reconstructed after the session, and each round of the 2\u21943 loop must re-declare against the new architecture.`
        );
      }
    }
    return out;
  }
  advancePhase(targetPhase) {
    if (!this.state) {
      return { ok: false, error: { message: "Project not initialized.", missingCriteria: [] } };
    }
    const from = this.state.currentPhase;
    const exitCriteriaMet = /* @__PURE__ */ new Map();
    for (const c of this.state.exitCriteria) {
      if (c.phase === from) {
        exitCriteriaMet.set(c.criterion, c.met);
      }
    }
    const validation = validatePhaseTransition(from, targetPhase, this.state, exitCriteriaMet);
    const specsWarnings = [];
    if (targetPhase >= 1) {
      const specsStatus = this.checkSpecsStatus();
      const expectedDirs = this.getExpectedSpecsDirs(from);
      for (const dir of expectedDirs) {
        if (specsStatus[dir] && !specsStatus[dir].populated) {
          specsWarnings.push(`specs/${dir}/ is empty (expected before Phase ${targetPhase})`);
        }
      }
    }
    const artifactMissing = this.missingEvidence(from);
    const moduleDrift = from === 2 ? this.moduleTraceabilityErrors() : [];
    const rowDrift = from === 2 ? this.findingRowErrors() : [];
    if (!validation.valid || artifactMissing.length > 0 || moduleDrift.length > 0 || rowDrift.length > 0) {
      return {
        ok: false,
        error: {
          message: `Cannot advance from Phase ${from} to Phase ${targetPhase}.`,
          missingCriteria: [...validation.missingCriteria, ...artifactMissing, ...moduleDrift, ...rowDrift],
          safeguardViolations: validation.safeguardViolations,
          specsWarnings
        }
      };
    }
    this.state.history.push({
      from,
      to: targetPhase,
      timestamp: (/* @__PURE__ */ new Date()).toISOString(),
      criteriaMet: Array.from(exitCriteriaMet.entries()).filter(([, met]) => met).map(([criterion]) => criterion)
    });
    this.state.currentPhase = targetPhase;
    this.state.currentIteration = 1;
    this.resetLoopCounter();
    if (targetPhase < from) {
      for (const ec of this.state.exitCriteria) {
        if (ec.phase >= targetPhase && ec.phase <= from) ec.met = false;
      }
    }
    this.save();
    return { ok: true, value: void 0 };
  }
  startIteration(phase) {
    if (!this.state) {
      return { ok: false, error: "Project not initialized." };
    }
    if (this.state.currentPhase !== phase) {
      return { ok: false, error: `Current phase is ${this.state.currentPhase}, not ${phase}.` };
    }
    this.state.currentIteration += 1;
    this.save();
    return {
      ok: true,
      value: {
        phase,
        iterationNumber: this.state.currentIteration
      }
    };
  }
  // --- Recording ---
  recordDecision(phase, category, content) {
    if (!this.state) throw new Error("Project not initialized.");
    const decision = {
      id: (0, import_crypto.randomUUID)(),
      phase,
      category,
      content,
      timestamp: (/* @__PURE__ */ new Date()).toISOString()
    };
    this.state.decisions.push(decision);
    this.save();
    if (DIAGNOSIS_CATEGORIES.includes(category.trim().toLowerCase())) {
      this.clearLoopCredit();
    }
    return decision;
  }
  updateProjectSpec(spec) {
    if (!this.state) throw new Error("Project not initialized.");
    if (!this.state.projectSpec) {
      this.state.projectSpec = { stack: [], outOfScope: [], patterns: [], constraints: [] };
    }
    const ps = this.state.projectSpec;
    const at = (/* @__PURE__ */ new Date()).toISOString();
    const phase = this.state.currentPhase;
    const merge = (existing, added) => {
      const have = new Set(existing.map(specEntryValue));
      const out = [...existing];
      for (const v of added) {
        if (!have.has(v)) {
          out.push({ value: v, phase, at });
          have.add(v);
        }
      }
      return out;
    };
    if (spec.stack) ps.stack = merge(ps.stack, spec.stack);
    if (spec.outOfScope) ps.outOfScope = merge(ps.outOfScope, spec.outOfScope);
    if (spec.patterns) ps.patterns = merge(ps.patterns, spec.patterns);
    if (spec.constraints) ps.constraints = merge(ps.constraints, spec.constraints);
    this.save();
  }
  getProjectSpec() {
    if (!this.state) throw new Error("Project not initialized.");
    const ps = this.state.projectSpec ?? { stack: [], outOfScope: [], patterns: [], constraints: [] };
    return {
      stack: ps.stack.map(specEntryValue),
      outOfScope: ps.outOfScope.map(specEntryValue),
      patterns: ps.patterns.map(specEntryValue),
      constraints: ps.constraints.map(specEntryValue)
    };
  }
  updateScore(score, breakdown) {
    if (!this.state) throw new Error("Project not initialized.");
    this.state.phase0Score = score;
    this.state.phase0Breakdown = breakdown;
    this.save();
  }
  markExitCriterion(phase, criterion, met, details) {
    if (!this.state) throw new Error("Project not initialized.");
    const existing = this.state.exitCriteria.find(
      (c) => c.phase === phase && c.criterion === criterion
    );
    if (existing) {
      existing.met = met;
      existing.details = details;
    } else {
      this.state.exitCriteria.push({ phase, criterion, met, details });
    }
    this.save();
  }
  markExitCriteria(entries) {
    if (!this.state) throw new Error("Project not initialized.");
    for (const e of entries) {
      const existing = this.state.exitCriteria.find(
        (c) => c.phase === e.phase && c.criterion === e.criterion
      );
      if (existing) {
        existing.met = e.met;
        existing.details = e.details;
      } else {
        this.state.exitCriteria.push({ phase: e.phase, criterion: e.criterion, met: e.met, details: e.details });
      }
    }
    this.save();
  }
  // --- Safeguards ---
  checkSafeguard(id) {
    if (!this.state) {
      return { id, status: "ok", details: "Project not initialized." };
    }
    const result = validateSafeguard(id, this.state);
    const sg = this.state.safeguards.find((s) => s.id === id);
    if (sg) {
      sg.status = result.status;
      sg.details = result.details;
      sg.lastChecked = (/* @__PURE__ */ new Date()).toISOString();
      this.save();
    }
    return result;
  }
  checkAllSafeguards() {
    if (!this.state) return [];
    const results = getSafeguardsForPhase(this.state.currentPhase).map((s) => validateSafeguard(s.id, this.state));
    for (const result of results) {
      const sg = this.state.safeguards.find((s) => s.id === result.id);
      if (sg) {
        sg.status = result.status;
        sg.details = result.details;
        sg.lastChecked = (/* @__PURE__ */ new Date()).toISOString();
      }
    }
    this.save();
    return results;
  }
  // --- Specs ---
  checkSpecsStatus() {
    const dirs = [
      "references",
      "domain",
      "technical",
      "examples",
      "design",
      "models",
      "datasets",
      "validation",
      "competitors"
    ];
    const status = {};
    for (const dir of dirs) {
      const dirPath = path.join(this.specsPath, dir);
      try {
        if (fs.existsSync(dirPath)) {
          const files = fs.readdirSync(dirPath).filter((f) => f !== "README.md");
          status[dir] = { populated: files.length > 0, fileCount: files.length };
        } else {
          status[dir] = { populated: false, fileCount: 0 };
        }
      } catch {
        status[dir] = { populated: false, fileCount: 0 };
      }
    }
    return status;
  }
  // --- Loop Counter (S6) ---
  /**
   * Records the outcome of a test run. Only FAILURES accumulate: a green run is
   * the end of the work, never a loop, so it clears the counter. Blocking is
   * decided by the caller reading getLoopCounter() BEFORE the run.
   */
  recordTestOutcome(command, failed) {
    if (!this.state) return { count: 0 };
    this.state.lastTestOutcome = {
      outcome: failed ? "fail" : "pass",
      phase: this.state.currentPhase,
      at: (/* @__PURE__ */ new Date()).toISOString()
    };
    if (!failed) {
      this.resetLoopCounter();
      return { count: 0 };
    }
    const normalized = this.normalizeCommandPattern(command);
    const counter = this.state.loopCounter;
    const now = (/* @__PURE__ */ new Date()).toISOString();
    if (counter && counter.pattern === normalized && counter.count > 0) {
      counter.count += 1;
      counter.lastSeen = now;
    } else {
      this.state.loopCounter = {
        pattern: normalized,
        count: 1,
        firstSeen: now,
        lastSeen: now,
        lastDiagnosis: counter?.lastDiagnosis
      };
    }
    this.save();
    return { count: this.state.loopCounter.count };
  }
  /**
   * A named diagnosis was recorded — the failures so far are understood, not
   * blind. Clears the counter and lets the next run through. This is the escape
   * hatch the S6 block message promises.
   */
  clearLoopCredit() {
    if (!this.state) return;
    const now = (/* @__PURE__ */ new Date()).toISOString();
    this.state.loopCounter = {
      pattern: "",
      count: 0,
      firstSeen: "",
      lastSeen: "",
      lastDiagnosis: now
    };
    this.save();
  }
  resetLoopCounter() {
    if (!this.state) return;
    this.state.loopCounter = {
      pattern: "",
      count: 0,
      firstSeen: "",
      lastSeen: "",
      lastDiagnosis: this.state.loopCounter?.lastDiagnosis
    };
    this.save();
  }
  /** True when undiagnosed failures reached the threshold — next test run is blocked. */
  isLoopBlocked() {
    return this.getLoopCounter().count >= LOOP_FAILURE_THRESHOLD;
  }
  getLoopCounter() {
    if (!this.state || !this.state.loopCounter) return { pattern: "", count: 0 };
    const c = this.state.loopCounter;
    return { pattern: c.pattern, count: c.count, lastDiagnosis: c.lastDiagnosis };
  }
  /**
   * Normalizes a test command into a pattern. The suite/target argument is kept:
   * S6 talks about iterations on the same MODULE, so `npm test -- consent` and
   * `npm test -- link` must not collapse into the same pattern.
   */
  normalizeCommandPattern(cmd) {
    const trimmed = cmd.trim().toLowerCase();
    let runner = "";
    if (/\b(npm\s+test|npm\s+run\s+test|npx\s+jest|jest|vitest|mocha)\b/.test(trimmed)) runner = "test:js";
    else if (/\b(pytest|python\s+-m\s+pytest|unittest)\b/.test(trimmed)) runner = "test:py";
    else if (/\bcargo\s+test\b/.test(trimmed)) runner = "test:rust";
    else if (/\bgo\s+test\b/.test(trimmed)) runner = "test:go";
    else if (/\bnpm\s+run\s+build\b/.test(trimmed)) runner = "build";
    else if (/\btsc\b/.test(trimmed)) runner = "compile";
    else return trimmed.substring(0, 50);
    const target = trimmed.replace(/^.*?\b(npm\s+run\s+test|npm\s+test|npx\s+jest|jest|vitest|mocha|pytest|python\s+-m\s+pytest|unittest|cargo\s+test|go\s+test|npm\s+run\s+build|tsc)\b/, "").replace(/(^|\s)--?[\w-]+(=\S+)?/g, " ").replace(/\s+/g, " ").trim();
    return target ? `${runner}:${target}` : runner;
  }
  // --- Meta-iteration (v1.0 → v2.0) ---
  startNewCycle() {
    if (!this.state) {
      return { ok: false, error: "Project not initialized." };
    }
    if (this.state.currentPhase !== 7) {
      return { ok: false, error: `Current phase is ${this.state.currentPhase}. New cycle can only start from Phase 7 (Post-Review).` };
    }
    const p7Criteria = this.state.exitCriteria.filter((c) => c.phase === 7);
    const unmet = p7Criteria.filter((c) => !c.met);
    if (unmet.length > 0) {
      return { ok: false, error: `Phase 7 exit criteria not met: ${unmet.map((c) => c.criterion).join(", ")}. Complete Post-Review before starting new cycle.` };
    }
    const missing = this.missingEvidence(7);
    if (missing.length > 0) {
      return { ok: false, error: missing.join(" ") };
    }
    const cycleCount = this.state.history.filter((h) => h.to === 7).length + 1;
    this.state.history.push({
      from: 7,
      to: 0,
      timestamp: (/* @__PURE__ */ new Date()).toISOString(),
      criteriaMet: p7Criteria.map((c) => c.criterion)
    });
    this.state.currentPhase = 0;
    this.state.currentIteration = 1;
    this.state.phase0Score = null;
    this.state.phase0Breakdown = null;
    this.state.exitCriteria = [];
    this.state.safeguards = [
      { id: "S0", status: "ok" },
      { id: "S1", status: "ok" },
      { id: "S2", status: "ok" },
      { id: "S3", status: "ok" },
      { id: "S4", status: "ok" },
      { id: "S5", status: "ok" },
      { id: "S6", status: "ok" },
      { id: "S7", status: "ok" }
    ];
    this.resetLoopCounter();
    this.save();
    return { ok: true, value: { cycle: cycleCount + 1 } };
  }
  // --- Private helpers ---
  getExpectedSpecsDirs(phase) {
    switch (phase) {
      case 0:
        return ["references", "domain", "competitors"];
      case 1:
        return ["technical", "models", "examples"];
      case 5:
        return ["technical", "examples", "datasets"];
      case 6:
        return ["datasets", "validation"];
      default:
        return [];
    }
  }
};

// src/hooks/stop-verify.ts
var import_child_process = require("child_process");
function block(reason) {
  const output = { decision: "block", reason };
  process.stdout.write(JSON.stringify(output) + "\n");
  process.exit(2);
}
function warn(msg) {
  const output = { additionalContext: msg };
  process.stdout.write(JSON.stringify(output) + "\n");
  process.exit(0);
}
function pass() {
  process.exit(0);
}
function run(cmd, args, cwd) {
  const result = (0, import_child_process.spawnSync)(cmd, args, {
    cwd,
    encoding: "utf-8",
    timeout: 6e4,
    shell: true
  });
  const output = ((result.stdout || "") + (result.stderr || "")).trim();
  return { ok: result.status === 0, output };
}
function main() {
  const workspacePath = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const engine = new StateEngine(workspacePath);
  const state = engine.getPhaseState();
  if (!state) {
    pass();
    return;
  }
  if (state.currentPhase < 5) {
    pass();
    return;
  }
  let input = "";
  process.stdin.setEncoding("utf-8");
  const timeoutId = setTimeout(() => {
    process.stdin.destroy();
    pass();
  }, 5e3);
  process.stdin.on("data", (chunk) => {
    input += chunk;
  });
  process.stdin.on("end", () => {
    clearTimeout(timeoutId);
    try {
      const hookInput = JSON.parse(input);
      if (hookInput.stop_hook_active) {
        pass();
        return;
      }
    } catch {
    }
    const fs2 = require("fs");
    const path2 = require("path");
    const errors = [];
    let checksRun = 0;
    if (fs2.existsSync(path2.join(workspacePath, "tsconfig.json"))) {
      checksRun++;
      const r = run("npx", ["tsc", "--noEmit"], workspacePath);
      if (!r.ok) {
        const lines = r.output.split("\n").slice(0, 30).join("\n");
        errors.push(`TYPE CHECK FAILED:
${lines}`);
      }
    }
    const eslintConfigs = [
      ".eslintrc",
      ".eslintrc.js",
      ".eslintrc.json",
      ".eslintrc.yml",
      "eslint.config.js",
      "eslint.config.mjs",
      "eslint.config.ts"
    ];
    if (eslintConfigs.some((c) => fs2.existsSync(path2.join(workspacePath, c)))) {
      checksRun++;
      const r = run("npx", ["eslint", ".", "--quiet"], workspacePath);
      if (!r.ok) {
        const lines = r.output.split("\n").slice(0, 30).join("\n");
        errors.push(`LINT FAILED:
${lines}`);
      }
    }
    const hasPython = ["pyproject.toml", "setup.py", "setup.cfg"].some((f) => fs2.existsSync(path2.join(workspacePath, f)));
    if (hasPython) {
      const mypyConf = fs2.existsSync(path2.join(workspacePath, "mypy.ini"));
      let mypyInPyproject = false;
      try {
        const pyproject = fs2.readFileSync(path2.join(workspacePath, "pyproject.toml"), "utf-8");
        mypyInPyproject = pyproject.includes("[tool.mypy]");
      } catch {
      }
      if (mypyConf || mypyInPyproject) {
        checksRun++;
        const r = run("mypy", ["."], workspacePath);
        if (!r.ok) {
          const lines = r.output.split("\n").slice(0, 30).join("\n");
          errors.push(`MYPY FAILED:
${lines}`);
        }
      }
      const ruffCheck = (0, import_child_process.spawnSync)("which", ["ruff"], { encoding: "utf-8", shell: true });
      if (ruffCheck.status === 0) {
        checksRun++;
        const r = run("ruff", ["check", "."], workspacePath);
        if (!r.ok) {
          const lines = r.output.split("\n").slice(0, 30).join("\n");
          errors.push(`RUFF FAILED:
${lines}`);
        }
      }
    }
    if (fs2.existsSync(path2.join(workspacePath, "Cargo.toml"))) {
      checksRun++;
      const r = run("cargo", ["check"], workspacePath);
      if (!r.ok) {
        const lines = r.output.split("\n").slice(0, 30).join("\n");
        errors.push(`CARGO CHECK FAILED:
${lines}`);
      }
    }
    let testRunner = "";
    if (fs2.existsSync(path2.join(workspacePath, "package.json"))) {
      try {
        const pkg = JSON.parse(fs2.readFileSync(path2.join(workspacePath, "package.json"), "utf-8"));
        const testScript = pkg?.scripts?.test || "";
        if (testScript && !testScript.includes("no test specified")) {
          testRunner = "npm test";
        }
      } catch {
      }
    } else if (hasPython) {
      const pytestCheck = (0, import_child_process.spawnSync)("which", ["pytest"], { encoding: "utf-8", shell: true });
      if (pytestCheck.status === 0) {
        testRunner = "pytest --tb=short -q";
      }
    } else if (fs2.existsSync(path2.join(workspacePath, "Cargo.toml"))) {
      testRunner = "cargo test";
    }
    if (testRunner) {
      checksRun++;
      const parts = testRunner.split(" ");
      const r = run(parts[0], parts.slice(1), workspacePath);
      if (!r.ok) {
        const lines = r.output.split("\n").slice(-30).join("\n");
        errors.push(`TESTS FAILED (${testRunner}):
${lines}`);
      }
    }
    if (errors.length > 0) {
      block(
        `[Versus] Stop verification failed (${checksRun} checks ran). Fix these errors before completing:

${errors.join("\n\n")}`
      );
    } else if (checksRun === 0) {
      warn(
        "[Versus] No type-checker, linter, or test suite detected. Task completion is unverified. State this to the user."
      );
    } else {
      pass();
    }
  });
}
main();
