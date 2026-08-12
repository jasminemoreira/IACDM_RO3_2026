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
var PHASE_DEFINITIONS = [
  {
    number: 0,
    name: "Problem Discovery",
    description: "Iterative problem discovery loop. Score >= 90/100 to advance.",
    userHint: "Explore the problem thoroughly. No coding yet.",
    iterative: true
  },
  {
    number: 1,
    name: "Architecture",
    description: "Module, interface, pattern, and principle definitions.",
    userHint: "Design modules and interfaces. No coding yet.",
    iterative: false
  },
  {
    number: 2,
    name: "Adversarial Critique",
    description: "Attack architecture with specialized lenses. Generates coverage matrix.",
    userHint: "Challenge the architecture with adversarial lenses.",
    iterative: true
  },
  {
    number: 3,
    name: "Simplification",
    description: "Simplify architecture. Address Phase 2 critical findings.",
    userHint: "Simplify \u2014 address criticals without adding features.",
    iterative: true
  },
  {
    number: 4,
    name: "Convergence Gate",
    description: "Validate convergence: exit criteria from Phases 2-3 + safeguards S1-S5.",
    userHint: "Verify everything before implementation begins.",
    iterative: false
  },
  {
    number: 5,
    name: "Code Implementation",
    description: "Implement final architecture. One file per response.",
    userHint: "Implement code. Testing happens in Phase 6.",
    iterative: false
  },
  {
    number: 6,
    name: "Tests",
    description: "100% tests passing + manual exploratory testing.",
    userHint: "Write and run tests. Manual testing is mandatory.",
    iterative: false
  },
  {
    number: 7,
    name: "Post-Review",
    description: "Lessons learned, update specs/, methodology meta-iteration.",
    userHint: "Review lessons. Offer meta-iteration for next cycle.",
    iterative: false
  }
];
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
function getPhaseDefinition(phase) {
  return PHASE_DEFINITIONS.find((p) => p.number === phase);
}
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

// src/rules/full-guidance.ts
function renderLensTable(defs, withTrigger) {
  const header = withTrigger ? "| Lens | Central Question | Exclusive Failure Class | Activate when... |\n|------|-----------------|------------------------|------------------|" : "| Lens | Central Question | Exclusive Failure Class |\n|------|-----------------|------------------------|";
  const rows = defs.map(
    (l) => withTrigger ? `| ${l.name} | ${l.question} | ${l.failureClass} | ${l.trigger} |` : `| ${l.name} | ${l.question} | ${l.failureClass} |`
  );
  return [header, ...rows].join("\n");
}
var GLOBAL_RULES = {
  R1: "R1: Evaluate triggers before coding. If triggered \u2192 Phase 0. Never skip to implementation.",
  R2: "R2: Every user decision via AskUserQuestion. ALWAYS provide suggested options (single or multi-select) \u2014 never send questions without options. Up to 4 questions/call. multiSelect for non-exclusive. Recommended first with '(Recommended)'. Never list options A/B/C in text.",
  R5: `R5: Mandatory Display \u2014 essential outputs MUST be shown in chat. Do NOT process internally without displaying.
Per phase:
- P0: Score breakdown table (all 10 criteria + weights + total). Teach-back synthesis (full 5-level template). Delivery Target question.
- P1: 4 architecture answers. Pattern summary table. Progressive Scope decision (if applicable). Technology comparison table (if >1 option).
- P2: Coverage matrix (modules \xD7 lenses with \u{1F534}\u{1F7E1}\u{1F7E2}). Concentration analysis (by module + by lens). Activated conditional lenses list. Exit gate summary.
- P3: Post-cycle decision (AI computes structural change % and criticals, presents recommendation, user confirms). Anti-scope-creep checklist verification. LOC justification (if >10% increase).
- P4: Convergence verification report (exit criteria + safeguards + specs status). LLM Switch Point decision (asked, not announced).
- P5: Progress announcements ("X/N completed, next: Y") after each file.
- P6: Test Map (spec\u2192test\u2192type). Spec Coverage Report (COVERED/NOT COVERED/GAPS). Testing status record (TESTING STATUS / PASS / FAIL / NEXT). Manual testing report.
- P7: Product evaluation. Project lessons (domain, stack, patterns, wrong assumptions). Meta-iteration offer.
Rule: If you computed it, SHOW it. The user cannot validate what they cannot see.`,
  R4_TIMING: {
    0: "R4: Populate specs/ \u2014 refs, domain, competitors.",
    1: "R4: Populate specs/ \u2014 technical, models, examples.",
    5: "R4: Consult specs/technical, examples, references, datasets BEFORE each module.",
    6: "R4: Use specs/datasets (ground truth), specs/validation (criteria), specs/technical (ranges).",
    7: "R4: Update specs/validation (results), specs/technical (final decisions), specs/references."
  }
};
var ACTIVATION_TRIGGERS = `## ACTIVATION TRIGGERS

### Fundamental principle (Generative Invariance):
The methodology does NOT improve the model \u2014 it improves the PROCESS. The same LLM operates with or without the methodology. The difference is external verification at each gate.

### Adoption criterion (risk asymmetry):
Cost of applying to a simple project \u2248 20 min overhead. Cost of NOT applying to a complex project \u2248 hours/days of rework.
Formal rule: apply when C_methodology_overhead < P(error) \xD7 C_undetected_error.

### Evaluate in sequence BEFORE proposing implementation:
1. Does not involve creating/modifying code \u2192 Answer directly
2. Requirement has vague words ("fancy", "scalable") \u2192 USE METHODOLOGY
3. Involves architectural decision \u2192 USE METHODOLOGY
4. User mentioned methodology \u2192 MANDATORY
5. Signs of hidden complexity \u2192 USE METHODOLOGY

Complexity signals (just 1 is enough): multiple domains, external integrations, request doesn't fit in 1 sentence, AI can't visualize complete solution, uncertainty about complexity.
Golden rule: if you can't assert it's simple, it's not simple.

When activating: announce detected triggers, observed signals, phases 0-7 summary, declare no coding until passing through Phases 0-4.`;
var ANTIPATTERNS = `## ANTI-PATTERNS TO AVOID

| # | Anti-pattern | Description | Antidote |
|---|-------------|-------------|----------|
| AP1 | Validation theater | Asking the AI "is this design good?" \u2014 evaluation mode (judging what the AI produced) activates confirmation bias. Generation mode (producing new content) does not. | Operate in GENERATION mode: produce failure scenarios ("how does this fail?"), not quality judgments ("is this good?"). |
| AP2 | Complexity as false solution | When critique reveals fragility, adding components instead of simplifying. "Second-system effect" (Brooks). | Each iteration must simplify, not complexify. |
| AP3 | Monolithic session | Design, code, and tests in a single conversation. Context saturates and quality degrades. | One session per phase, one phase per module. |
| AP4 | Implicit assumption | The design works \u2014 as long as unlisted conditions are true. | Assumptions lens in Phase 2 + assumptions in Phase 1. |
| AP5 | Absence of human-AV | Relying exclusively on automated tests. Semantic adequacy and domain correctness require human judgment. | S4 expanded + mandatory manual testing. |
| AP6 | Skipping Phase 0 | Starting with architecture without understanding the problem. Wrong complexity propagates through all phases. Cost: 100\xD7. | S0: Score \u226590 mandatory. |
| AP7 | Coding without reference | Implementing algorithms without consulting specs/ or literature. The AI will generate plausible code with invented parameters. | S6: Tier 1/2/3 + specs/technical populated. |
| AP8 | Convergent perfectionism | Infinite cycles seeking "perfect" design. | Stop criterion: <15% change + 0 critical \u2192 advance. S2: stopping is the user's decision. |
| AP9 | Silent scope creep | Adding features during Phases 2-3 without operator approval. | S5: Scope is the user's. Phase 2-3 suggests, never decides. |
| AP10 | Silent scope deferral | Marking an exit criterion as met=true while textually noting "will be done in next cycle / out of scope for now / pending content". The criterion is NOT met \u2014 this defers scope without operator approval, the inverse of AP9. | Either reduce Delivery Target via record_decision and re-baseline, OR return to the appropriate phase and complete before advancing. Textual prose is NOT acceptable substitute for met=false. |`;
var PHASE_0_GUIDANCE = `## Phase 0 \u2014 Problem Discovery Loop
### Verification: Human-AV (operator validates synthesis and teach-back)

### MODE DETECTION (FIRST CHECK \u2014 before any other action):
Call get_decisions(phase=0) and look for AS-IS USE CASES, AS-IS DOMAIN VOCABULARY, or LOCKED CONSTRAINTS decisions. If present, init_project was called with bootstrap_data \u2014 you are in **DELTA MODE** (brownfield extension, not greenfield).

**DELTA MODE adjustments:**
- Skip HSA Level 1 (Domain) \u2014 already captured during bootstrap. Read specs/domain/AS-IS-vocabulary.md and specs/references/AS-IS-modules.md instead.
- Levels 2-5 focus on the NEW change/feature only, not the existing system. Use cases, processes, and product apply to the delta.
- Production Capacity Check asks about capacity to MODIFY the existing system (testing impact, migration, backward compatibility), not about producing a complete product from scratch.
- The Delivery Target question applies to the delta: "Complete delta" / "MVP delta" / "Prototype delta".
- Score criteria still apply (\u226590 to advance), but evaluated against the delta scope, not the entire system.
- Out of Scope (Level 5) MUST include "everything in the existing system not touched by this delta \u2014 see AS-IS decisions for boundaries".

If get_decisions returns NO AS-IS entries, you are in **GREENFIELD MODE**. Proceed with the standard P0 flow below.

### Step 0: Read ALL content from specs/ before asking questions. Build on what already exists.

### Step 0.5 \u2014 Delivery Target (MANDATORY FIRST QUESTION \u2014 before starting HSA):
Before any analysis, ask via AskUserQuestion: "What is the delivery target for this project?"
- Option 1: "Complete product" \u2014 all requirements delivered in a single cycle. No scope splitting unless a technical blocker exists.
- Option 2: "MVP first, then iterate" \u2014 minimal viable product, with deferred features planned for future cycles.
- Option 3: "Prototype / proof of concept" \u2014 disposable, for validation only.

Record the answer immediately: record_decision(category='scope', content='DELIVERY TARGET: ...').
This answer frames the ENTIRE HSA: depth of research, scope boundaries, and feasibility thresholds depend on it.
Do NOT begin Level 1 without this decision recorded.

### HIERARCHICAL SEMANTIC ANALYSIS (HSA) \u2014 5-level exploration:
Explore the problem systematically from the broadest context (Domain) to the concrete deliverable (Product). Each level builds on the previous. Use AskUserQuestion (R2) at every level.

---

### Level 1 \u2014 DOMAIN (Context & Vocabulary)
Establish the semantic universe of the problem before diving into specifics.

| Sub-area | Key Questions |
|----------|--------------|
| Vocabulary | Key terms and definitions. Synonyms to avoid? |
| Vague Terms | Clarify: "fancy"\u2192concrete, "scalable"\u2192N users, "fast"\u2192ms |
| Theoretical Field | What discipline(s) does this belong to? What foundational knowledge applies? |
| Methodologies | Are there established methodologies or standards in this domain? |
| Tools & Ecosystem | What tools, platforms, and libraries define this domain's landscape? |

**Technical AND scientific research (MANDATORY for specialized domains):**
If the project involves DSP, ML, bioinformatics, engineering, sciences etc.: research BEFORE architecture:
- **Scientific:** Peer-reviewed reference papers, theoretical foundations of the domain, applicable mathematical/physical models, constants and parameters validated by literature
- **Technical:** Candidate algorithms with trade-offs, reference implementations, published benchmarks, mature tools and libraries
- **Competitive:** Competing solutions, state of the art, known gaps
- Deposit EVERYTHING in specs/ (references, technical, competitors)
- Each numerical parameter MUST have a cited source (paper, standard, specification)
- Rule: "Do not implement an algorithm without a verifiable bibliographic reference"

---

### Level 2 \u2014 PROBLEM (5W1H)
Define the problem precisely using the 5W1H framework.

| Sub-area | Key Questions |
|----------|--------------|
| Why (Motivation) | Why is it needed? What happens without it? What pain does it solve? |
| Who (Actors) | Who are the users? Who are the stakeholders? Who is affected? |
| What (Scope) | What exactly needs to be done? What is the core capability? |
| When (Timing) | When is it needed? Are there temporal constraints, deadlines, sequences? |
| Where (Context) | Where does it run? What environment, platform, infrastructure? |
| How (Approach) | How should it work at a high level? Any mandatory approach or constraint? |

---

### Level 3 \u2014 ELEMENTS (Parts & Constraints)
Identify the concrete components, entities, and constraints of the system.

| Sub-area | Key Questions |
|----------|--------------|
| Components | What are the main parts/modules of the system? |
| Entities | What data entities, models, or domain objects exist? |
| Resources | What external resources are needed (APIs, DBs, services, files)? |
| Actors | What human or system actors interact with each component? |
| Constraints | Technical limitations, resource constraints. Assumed premises? |

---

### Level 4 \u2014 PROCESSES (Flows & Feasibility)
Map the dynamic behavior: how components interact, transform, and communicate.

| Sub-area | Key Questions |
|----------|--------------|
| Use Cases | 3-5 main scenarios (actor/objective/flow). Edge cases? |
| Relationships | How do components relate? What are the dependencies? |
| Transformations | What data transformations occur? What are the inputs/outputs? |
| Flows | What are the main execution flows? What triggers them? |
| Events | What events does the system react to? What does it emit? |
| Tech Feasibility | Does the target platform support the fundamental mechanisms? |

**Tech Feasibility (MANDATORY VERIFICATION):**
**LESSON LEARNED:** Tech feasibility of the target platform must be VERIFIED, not assumed.
Before advancing, answer EXPLICITLY:
- Does the target platform support the fundamental mechanisms needed? (APIs, protocols, extensibility)
- In porting/migration projects: does the destination platform have capability parity with the source?
- Which capabilities are ESSENTIAL vs. DESIRABLE? Is any essential one absent?

If any essential capability is absent \u2192 BLOCKER. Do not advance without resolution.
Do not cut scope to fit the technology. Compare alternatives with table (requirements \xD7 techs, LOC, libs, platform). Ask the user via AskUserQuestion.

---

### Level 5 \u2014 PRODUCT (Deliverables & Criteria)
Define what "done" looks like \u2014 the expected output and how to measure success.

| Sub-area | Key Questions |
|----------|--------------|
| Desired Result | What is the final deliverable? What does the user get? |
| Deliverables | Concrete artifacts: files, APIs, interfaces, documentation? |
| Success Criteria | How do we measure success? (measurable and verifiable) |
| Acceptance Criteria | What must be true for the user to accept the result? |
| Out of Scope (YAGNI) | What NOT to do, with cost/benefit justification |

Note: Delivery Target was already recorded in Step 0.5 \u2014 use get_decisions(category='scope') to confirm before defining Out of Scope (YAGNI).

---

### Production Capacity Check (MANDATORY when Delivery Target is "Complete product"):
After defining deliverables and success criteria in Level 5, explicitly verify with the user via AskUserQuestion:

> "Do you (or your team) have the capacity to PRODUCE all assets and content required to fulfill the Success Criteria within the stated timeline?"

Inventory required productions BEFORE asking \u2014 present a table to the user (\u26A0\uFE0F MUST DISPLAY):

| Asset Type | Required Quantity | Production Source |
|---|---|---|
| Authoring (scenes/screens/copy/scripts) | <count + estimated word/page volume> | <user authors / hired writer / AI-assisted / N/A> |
| Visual (illustrations/mockups/icons) | <count> | <original / royalty-free / hired / N/A> |
| Audio (music/SFX/voice) | <count + duration> | <original / royalty-free / hired / N/A> |
| Data (datasets/training/reference content) | <volume> | <available / to acquire / to generate / N/A> |
| External integrations | <list third-party APIs/services> | <existing accounts / to setup / N/A> |

If any line lacks a clear production plan, this is a **CAPACITY BLOCKER**. Possible resolutions (offer via AskUserQuestion):
1. **Confirm capacity** \u2014 user provides the production plan now (record_decision)
2. **Reduce scope** \u2014 change Delivery Target from "Complete product" to "MVP first" or split into cycles
3. **Accept the risk explicitly** \u2014 record_decision(category='constraint', content='CAPACITY GAP: <what is missing>, <agreed mitigation>')

**CAUTION:** Tech Feasibility (Level 4) verifies the platform CAN run it. Production Capacity verifies you CAN make it. Both are required. Without this check, the P0 score becomes false confidence \u2014 designing what cannot be produced. AP10 (silent scope deferral) almost always traces back to skipping this step.

---

### CROSS-CUTTING \u2014 Documentation & Research (all levels):
| Sub-area | Action |
|----------|--------|
| Documentation | Specs, RFCs, legacy code, issues. Content in specs/? |
| Web Research | If specs/ has critical gaps, ask user permission to research. Options: research and deposit / research and present / don't research. Cite source/URL in all deposited material. |

---

### SYNTHESIS (Teach-Back) \u2014 Mandatory template (\u26A0\uFE0F MUST DISPLAY full template in chat):
\`\`\`markdown
# My Understanding (Iteration N)

## Level 1 \u2014 Domain
### Vocabulary (term | understanding | example)
### Domain Context (field, methodologies, relevant standards)

## Level 2 \u2014 Problem
### Summary in 3 Sentences (problem, not solution)
### 5W1H (Why | Who | What | When | Where | How)

## Level 3 \u2014 Elements
### Components & Entities identified
### Constraints & Assumptions

## Level 4 \u2014 Processes
### Main Use Cases (actor/objective/flow/concrete example)
### Key Flows & Relationships

## Level 5 \u2014 Product
### Deliverables & Success Criteria (measurable and verifiable)
### Out of Scope (item | reason)

## Remaining Ambiguities
## Questions for Next Iteration
\`\`\`

### VALIDATION \u2014 via AskUserQuestion: correct / almost / incomplete / wrong
**CAUTION AP1 (Validation theater):** The human evaluates the WRITTEN SYNTHESIS, does not ask the AI if it's correct.

### CONVERGENCE ASSESSMENT (0-100) \u2014 use update_score() (\u26A0\uFE0F MUST DISPLAY breakdown table in chat):
| Criterion | Weight |
|-----------|--------|
| Problem Clarity | 10 |
| Complete Use Cases | 15 |
| Defined Vocabulary | 10 |
| Resolved Ambiguities | 15 |
| Explicit Out of Scope | 10 |
| Success Criteria | 10 |
| Validated Assumptions | 10 |
| Documentation/Research (technical+scientific) + specs/ | 5 |
| User Confirmed | 10 |
| AI Confident (can answer "why?" for every scope, assumption, and decision) | 5 |

\u226590 \u2192 Phase 1 | 70-89 \u2192 +1 iteration | <70 \u2192 multiple iterations
**If score < 90:** call start_iteration() to open the next iteration, then continue HSA focusing on the criteria with lowest scores. Do NOT offer to advance to Phase 1 \u2014 iterate until score \u2265 90.
**If score \u2265 90:** call advance_phase() to advance to Phase 1. Inform the user.
**CAUTION AP8 (Perfectionism):** Score \u226590 is sufficient. Don't aim for 100.

### Implementation Feasibility \u2014 evaluate per component:
- Tier 1: Does a mature lib exist? \u2192 USE IT
- Tier 2: Is there a documented algorithm with a reference implementation? \u2192 PORT IT
- Tier 3: Neither of the above. If complex domain \u2192 mandatory PoC before Phase 1`;
var PHASE_1_GUIDANCE = `## Phase 1 \u2014 Architecture
### Verification: Human-AV (operator validates adequacy and completeness)

### Step 0: Consult and populate specs/
Read specs/technical, examples, models, design. If critical technical/scientific material is missing, research and deposit BEFORE defining modules.

### The 4 questions architecture MUST answer:
1. **Decomposition.** What are the modules? What are their responsibilities? Where are the boundaries? (SRP, Separation of Concerns)
2. **Interfaces.** How do modules communicate? What are the contracts? (Design by Contract)
3. **Assumptions.** What does the system assume as true? Implicit assumptions are the most common source of failures. (Leveson)
4. **Negative scope.** What does the system deliberately NOT do? Conscious limitations prevent scope creep.

**If the project requires a user interface:** list it as an explicit module in the decomposition (e.g., "Web UI", "React SPA", "CLI"). Never leave UI as an implicit extension of a backend module \u2014 it must appear by name with its own interface contract and be within scope as a named deliverable.

### Granularity principle (E = I\u2080/C):
Each module must be understandable by the AI in a SINGLE interaction. If it doesn't fit in context with its dependencies, it needs to be decomposed. Interfaces work as "executable summaries" \u2014 the AI doesn't need module B's code, only B's interface.

### Step 1: Pattern and Principle Collection (2 AskUserQuestion calls):

**Call 1 (up to 4 questions):**
1. Architectural Pattern (single): Clean Architecture / Layered / Hexagonal / Modular Monolith
2. Cross-cutting Principles (multi): SOLID / KISS+YAGNI / DDD / Composition over Inheritance
3. Concurrency (single): Single-threaded / Actor Model / Message Queue / N/A

**Call 2 (up to 4 questions):**
4. Relevant GoF (multi): select the most pertinent + "None specific"
5. Fowler Patterns \u2014 Domain (single): Domain Model / Transaction Script / Table Module
6. Fowler Patterns \u2014 Data (single): Repository+Data Mapper / Active Record / Table Data Gateway

Present summary in table, confirm via AskUserQuestion.

### Technological Validation:
If >1 tech option: comparative table (requirements \xD7 techs, LOC, dependencies, LLM context consumption).
Assumptions verified with evidence (specs/technical), not assumed. **CAUTION AP4 (Implicit assumptions).**
If tech forces scope reduction \u2192 wrong tech.

### Progressive Scope:
**FIRST:** Check the Phase 0 delivery target decision (get_decisions with category='scope', look for 'DELIVERY TARGET').
- If "Complete product": do NOT offer v1.0/v2.0 scope splitting. All requirements must be delivered in a single cycle. Only split if there is an explicit TECHNICAL BLOCKER (missing platform capability, immature dependency, infeasible Tier 3 without PoC). If splitting is forced by a blocker, document the blocker clearly with record_decision().
- If "MVP first" or "Prototype": offer progressive scope as below.

When maturity/risk is unequal: maturity map (req | mature lib? | LOC | risk).
Offer via AskUserQuestion: progressive scope (v1.0 mature, v2.0 rest) / all in v1.0 / other.
Progressive scope \u2260 cut: preserves 100%, distributes across versions.
**The AI must NEVER reduce scope by preference \u2014 only by documented technical necessity.**

### Session planning (decoupled cycle):
Future work will follow independent sessions:
- Design Session (Phases 0-4): context = domain + constraints \u2192 architecture + interfaces
- Code Session (Phase 5): context = architecture + module interface \u2192 100% dedicated
- Test Session (Phase 6): context = interface + contract \u2192 no need for internal code
- Validation Session: CI/CD runs tests \u2192 AI only invoked for corrections
**CAUTION AP3 (Monolithic session):** Separating phases into distinct sessions preserves context efficiency.

### Exit: Persist structured spec before advancing (MANDATORY)
After user confirms architecture, call update_project_spec() with:
- stack: approved technologies (e.g., ["TypeScript", "React 18", "FastAPI", "PostgreSQL"])
- outOfScope: items the system deliberately will NOT do (mirrors negative scope from question 4)
- patterns: architectural patterns selected (e.g., ["Clean Architecture", "Repository pattern"])
- constraints: hard constraints that must survive model switches (e.g., ["Claude-only", "no external auth providers"])
This structured context is injected before every message in all phases \u2014 it is the primary mechanism for enforcing P1 decisions across sessions.

### Exit: Persist the architecture document (MANDATORY \u2014 the gate requires the file)
Write the architecture document to \`specs/technical/architecture.md\`. It MUST contain a **module table** \u2014 one row per module \u2014 so the canonical module list is machine-readable:

\`\`\`
| id   | module      | responsibility            | interface                     | depends-on |
|------|-------------|---------------------------|-------------------------------|------------|
| M-01 | rate-limiter| enforce per-key quota     | allow(key) -> {ok, retryAfter}| store      |
| M-02 | store       | persist counters with TTL | incr(key, ttl) -> count       | \u2014          |
\`\`\`

The \`id\` (M-01, M-02, \u2026) exists only to make the row machine-recognizable; the **stable key across phases is the \`module\` name** in column 2. Phase 2's coverage matrix and Phase 5's implementation MUST use these exact names \u2014 if Phase 1 names a module \`rate-limiter\`, Phase 2 must not write \`quota\` and Phase 5 must not build \`limiter\`, or the coverage matrix's per-module traceability breaks and a post-mortem cannot close. Below the table, add the assumptions list.

\`advance_phase()\` to Phase 2 is BLOCKED until \`specs/technical/architecture.md\` exists AND contains module rows with ids (M-\\d+) \u2014 a prose doc no longer passes. As with the coverage matrix, the engine checks the FORM (there is a module table), not whether the architecture is good, nor \u2014 yet \u2014 that Phase 2 actually reused these names (that cross-check is not mechanized; see below). That stays your and the user's judgment.

Then call advance_phase() to move to Phase 2. Then call get_phase_guidance() and begin Phase 2 immediately: record activated lenses and start the adversarial critique.`;
var PHASE_2_GUIDANCE = `## Phase 2 \u2014 Adversarial Critique
### Verification: Human-AV + AG (7 universal + up to 12 conditional lenses as operationally distinct AVs)

### Critique-response asymmetry principle:
**Phase 2 = MULTIPLE agents to ATTACK** (lens diversity is value).
**Phase 3 = UNIFIED agent to RESPOND** (corrections must be integrated into the whole).
**Human operator = ARBITRATE trade-offs** (systemic vision).
Different lenses see different flaws. Isolated responses may be individually correct but systemically contradictory.

### Universal Lenses (ALL always applied \u2014 low cost in planning, high risk if omitted):
${renderLensTable(UNIVERSAL_LENS_DEFS, false)}

Selection principle: if removing this lens, is there a failure class that NO other lens detects? If yes \u2192 legitimate. If not \u2192 redundancy.

### Conditional Lenses (activate based on project context from ProjectSpec):
${renderLensTable(CONDITIONAL_LENS_DEFS, true)}

Conditional lens activation (STEP 1, before applying any lens): review ProjectSpec (stack, constraints, out-of-scope) and decide, for EACH of the 12 conditional lenses, whether this project activates it. Record with \`record_activated_lenses(conditional=[...], notActivated=[{lens, reason}, ...])\` \u2014 the STRUCTURED tool, NOT prose in record_decision. All 12 must be accounted for: activated, or not-activated with a concrete one-line reason. The tool validates names against the canonical set (so an abbreviation or a translation is refused at the call), and stamps the record with the current critique iteration and architecture version automatically \u2014 that is the same N you head the matrix with (\`## Itera\xE7\xE3o N \u2014 V(N)\`). \`advance_phase()\` to Phase 3 is BLOCKED until this record exists for the current iteration.

**Re-declare each round of the 2\u21943 loop.** When you return to Phase 2 to critique V(N+1), the lens set is re-examined against the NEW architecture \u2014 a set fixed against V(1) while the design changes is a defect. The engine resets \`activated_lenses_recorded\` on loop-back and stamps the fresh record with the new iteration, so call \`record_activated_lenses\` again each round. A finding may only carry a lens that was declared for ITS iteration \u2014 the engine checks the matrix's \`lens\` column against the set declared for that round.

**Activation is by PROJECT SIGNAL only.** That another lens seems to cover the same failure class is NOT a reason to skip a lens: absence of findings is already a valid result, and deciding in advance that two lenses overlap is the conclusion the study measures, not a premise. Never drop a lens for redundancy with another \u2014 the individual reason for a non-activated lens must be a project signal ("no external dependencies", "no user-facing surface"), never "already covered by lens X".

### Protocol per lens:
1. Apply central question to EACH module
2. Classify findings: \u{1F534} Critical (blocks) | \u{1F7E1} Important (degrades) | \u{1F7E2} Suggestion
3. Finding = concrete evidence, not opinion
4. Passes are independent (one lens at a time)
**GENERATION MODE:** Phase 2 operates in generative mode \u2014 produce failure scenarios, not quality judgments. "How does this module fail?" generates new content (no confirmation bias anchor). "Is this design good?" asks the AI to evaluate what it produced (confirmation bias activated). The lens central questions are already in generative mode \u2014 follow them as written.

### Coverage Matrix (mandatory) (\u26A0\uFE0F MUST DISPLAY the findings in chat \u2014 do NOT summarize or skip modules/lenses):
Record every finding from every applied lens (universal + activated conditional) on every module. You MAY render a readable module\xD7lens severity grid in chat, but the PERSISTED artifact is a findings table \u2014 never a grid.

**PERSIST IT AS A FINDINGS TABLE \u2014 the criterion is not met until the file has this form.** Write \`specs/design/coverage-matrix.md\` as ONE ROW PER FINDING, not a severity-per-cell grid:

\`\`\`
## Itera\xE7\xE3o 1 \u2014 V(1)

| id | module | lens | severity | description |
|------|--------|----------|----------|-------------|
| P-01 | auth   | Security | \u{1F534} | login builds SQL by string concat \u2192 injection |
| A-03 | auth   | Architectural | \u{1F7E1} | auth imports ui for its error toast \u2192 cycle |
| P-02 | auth   | Security | \u{1F534} | duplica: none \u2014 session token never expires |
\`\`\`

**Head each round's findings with a section line \`## Itera\xE7\xE3o N \u2014 V(N)\`** (the same N and V as that round's lens declaration). When the 2\u21943 loop runs again, APPEND a new \`## Itera\xE7\xE3o N+1 \u2014 V(N+1)\` section with that round's findings \u2014 do NOT overwrite the earlier ones. Without the header every finding silently collapses into iteration 1, and which architecture version a finding was against is lost.

Rules: every finding gets a **unique id in this project** (P-01, A-03, \u2026 \u2014 use a consistent prefix per lens, the SAME prefix every time that lens appears). **The prefix \`M-\` is RESERVED for modules (Phase 1's architecture table) \u2014 never use it for a finding; the Mechanical Engineering lens uses \`MEC-\`, not \`M-\`.** In the **\`lens\` column use the EXACT lens name from the Phase 2 lens table** (Security, Architectural, Resilience, \u2026) \u2014 never an abbreviation or a translation, because cross-project analysis groups on this column and a "Seguran\xE7a"/"SEG"/"Security" split makes the data unaggregatable. Use the exact Phase-1 module name in the \`module\` column. When a finding is **the same defect** another lens already recorded, add \`duplica: <that id>\` in the description. **This applies WITHIN the same lens too:** if one lens records the same defect twice under two ids, mark the second \`duplica: <first id>\`. A lens double-counting one defect inflates its own exclusive contribution, which is exactly the quantity the study measures. This per-finding format \u2014 not a grid of severities \u2014 is the whole point: it is what lets a later analysis (or a post-mortem when \`auth\` breaks) tell two lenses finding the SAME defect (overlap) from two lenses finding DIFFERENT defects in the same module (orthogonality). You MAY still display a readable module\xD7lens grid in chat, but the PERSISTED file must be the findings table.

\`advance_phase()\` to Phase 3 is BLOCKED until the file exists AND contains findings rows with ids (the engine checks the form, not whether the findings are real or the \`duplica\` marks honest \u2014 that stays your and the user's judgment). The engine now ALSO checks the \`lens\` column of every finding: it must be one of the 19 canonical names (case and the spacing around \`/\` are tolerated; abbreviations and translations are not), or the literal \`NENHUMA\` for a finding that fit no lens \u2014 and a conditional lens must have been declared for that finding's iteration via record_activated_lenses. A row with \`Sustainability\` instead of \`Sustainability / Proportionality\`, or a lens not activated for its round, blocks the advance and names the row. The \`severity\` column is checked the same way: exactly one of \u{1F534} / \u{1F7E1} / \u{1F7E2} (a trailing word is fine, "high" or "P1" or an empty cell is not) \u2014 the analysis counts criticals vs important on it.

### Concentration analysis (MANDATORY after the matrix) (\u26A0\uFE0F MUST DISPLAY analysis in chat):
- **Concentration by module:** Module with findings across ALL lenses \u2192 probably poorly conceived \u2192 requires REDESIGN, not patch.
- **Concentration by lens:** Lens with findings across ALL modules \u2192 SYSTEMIC failure (e.g.: no parameter has a reference, no module testable in isolation).
- Document concentration patterns with record_decision().

### Exit Gate (\u26A0\uFE0F MUST DISPLAY gate summary in chat \u2014 show total \u{1F534}/\u{1F7E1}/\u{1F7E2} counts):
- \u{1F534} Criticals \u2192 will be addressed in Phase 3. Do NOT block advancement \u2014 Phase 3 exists precisely to resolve criticals.
- \u{1F7E1} Important \u2192 Phase 3 addresses them or records explicit acceptance with justification (record_decision)
- \u{1F7E2} Suggestions \u2192 can be deferred to v2.0 (record_decision)
- Zero findings across ALL lenses is a RED FLAG, not a clean bill: an adversarial pass over the universal + activated lenses that finds nothing almost always means the critique was shallow or the modules too coarse. Revisit \u2014 a real Phase 2 leaves at least one finding, and the gate to Phase 3 requires the findings table to contain it.

### Next Step (MANDATORY after displaying gate summary):
Phase 3 always follows Phase 2. After displaying the gate:
- If any findings (\u{1F534}/\u{1F7E1}/\u{1F7E2}) \u2014 the normal case: call advance_phase() \u2192 Phase 3. Inform: "Advancing to Phase 3 to address [N \u{1F534} criticals, N \u{1F7E1} important]."
- If you believe there are zero findings: revisit the critique first (rare after a genuine adversarial pass). The only valid transition from Phase 2 is to Phase 3 \u2014 there is no skip to Phase 4.
Do NOT stop and wait. Do NOT block on \u{1F534} count \u2014 criticals are addressed IN Phase 3, not before entering it.

### BOUNDARY RULE (Scope vs Architecture):
Phase 2-3 CAN: change libs/patterns/communication, simplify modules, add technical mechanisms.
Phase 2-3 CANNOT: cut requirements, add features, change target audience/use cases.
TEST: "Does this change WHAT the system does?" or "WHO it serves?" \u2192 If yes = SCOPE \u2192 back to Phase 0.
**CAUTION AP9 (Silent scope creep).**`;
var PHASE_3_GUIDANCE = `## Phase 3 \u2014 Simplification
### Verification: Human-AV (operator validates that complexity decreased and scope preserved)

### Asymmetry principle (continuation of Phase 2):
Phase 2 attacked with MULTIPLE lenses. Phase 3 responds with UNIFIED VISION.
Individually correct corrections may be systemically contradictory.
Integrate all responses into the whole \u2014 don't correct module by module in isolation.
Trade-offs resolved by the HUMAN OPERATOR (S2: stopping criterion is the user's).

### Step 0 \u2014 Read the persisted coverage matrix (MANDATORY, before addressing anything):
Read \`specs/design/coverage-matrix.md\` \u2014 the findings table Phase 2 wrote. Do NOT work from memory of the chat. Address the \u{1F534} criticals and \u{1F7E1} important findings **by id**, row by row: when you resolve P-01, say so and how. Findings marked \`duplica:\` are the same defect seen twice \u2014 resolve the defect once. This is the asset being acted on, not just stored, and referencing findings by id is what keeps the audit trail honest (a later post-mortem can check whether P-01 was actually addressed).

### Updating the architecture doc: APPEND V(N+1), never overwrite V(N).
Add a new \`## V(N+1)\` section to \`specs/technical/architecture.md\`, with its own module
table \u2014 do NOT replace the previous one. The Phase 2\u21943 loop critiques a DIFFERENT architecture
each round: a finding from iteration 1 can name a module that V(2) removed. Overwrite it and
that finding points at a module no artifact records any more, so the per-module traceability
the coverage matrix exists for breaks exactly where the design changed most. Keep every
version; the last section is the current one.

### Purpose: Simplify V(N) \u2192 V(N+1), eliminating complexity.
**CAUTION AP2 (Complexity as false solution):** Each iteration must SIMPLIFY, not complexify.

### Mandatory distinction:
- Adding Worker/cache/fallback = architecture (OK)
- Adding tutorial/button/animation = feature (FORBIDDEN)

### If LOC increased >10%: MANDATORY justification documented with record_decision().

### Post-cycle 2-3 decision (\u26A0\uFE0F MUST DISPLAY \u2014 the AI computes, the user confirms):
**The user CANNOT know the structural change % \u2014 only the AI can compute it.** Do NOT ask the user to choose a percentage range. Instead:

**Step 1 \u2014 Compute (AI does this):**
- Compare V(N) architecture with V(N+1): count modules added, removed, or significantly restructured
- Structural change % = (modules changed / total modules) \xD7 100
- Count remaining \u{1F534} criticals from the Phase 2 matrix that were NOT resolved

**Step 2 \u2014 Present (\u26A0\uFE0F MUST DISPLAY in chat):**
Show the computed values AND the reference table:
\`\`\`
Structural change: X% (Y of Z modules changed)
Remaining criticals: N
\`\`\`
| Structural change | Critical | Action |
|---|---|---|
| <15% | 0 | \u2192 Phase 4 |
| 15-25% | 0-1 | 1 more iteration |
| >25% | 2+ | Multiple iterations |

**Recommended action: [action based on computed values]**

**Step 3 \u2014 Confirm (via AskUserQuestion):**
Present the recommendation and ask: accept recommendation / override (user chooses different action).
The user validates the RECOMMENDATION, not the raw data.

**Step 4 \u2014 Execute the agreed action (do NOT stop after confirmation):**
- "\u2192 Phase 4": call advance_phase(), then call get_phase_guidance() and begin Phase 4 convergence verification immediately.
- "1 more iteration" or "Multiple iterations": call start_iteration(), then return to Phase 2 critique with the updated architecture V(N+1). Announce: "Starting iteration N of the 2-3 loop. Returning to Phase 2 critique \u2014 apply all lenses to V(N+1)."

**CAUTION AP8 (Perfectionism):** The stopping criterion is honesty \u2014 we know what works, what we assume, and what we don't know.

### Anti-Scope-Creep Checklist (MANDATORY before advancing) (\u26A0\uFE0F MUST DISPLAY checklist with \u2705/\u274C in chat):
1. ALL Phase 0 requirements covered
2. No unsolicited features added
3. What the system DOES hasn't changed (only HOW)
4. Phase 0 use cases remain valid`;
var PHASE_4_GUIDANCE = `## Phase 4 \u2014 Convergence Gate
### Verification: Human-AV (operator validates convergence with rigorous criteria)

Validate complete convergence \u2014 this gate decides if the design is ready for code (\u26A0\uFE0F MUST DISPLAY convergence verification report with \u2705/\u274C per item):

1. \u2705/\u274C Verify ALL exit criteria of Phases 2-3 (use get_exit_criteria for Phase 2 and Phase 3)
2. \u2705/\u274C Verify ALL safeguards S1-S5 (use check_all_safeguards)
3. \u2705/\u274C Verify: are the 4 P1 questions still answered? (Decomposition, Interfaces, Assumptions, Negative scope)
4. \u2705/\u274C Verify: did the matrix concentration analysis reveal unresolved systemic failures?
5. \u2705/\u274C Verify: is specs/ populated with technical and scientific references needed for Phase 5?
6. Only advance to Phase 5 if EVERYTHING is \u2705
7. If something is \u274C \u2192 return to Phase 2 or 3 as needed

**CAUTION AP6 (Skipping phases):** Don't advance with pending items. The cost of discovering problems in Phase 5-6 is 10\xD7 higher than solving them here.

### LLM Switch Point (\u26A0\uFE0F MUST DISPLAY this notification to the user):
Phase 4 is the natural boundary for switching LLMs to reduce cost. Phases 0-4 (design) require high reasoning capability \u2014 use the most capable model available. Phases 5-7 (implementation, tests, review) require code generation and execution \u2014 a cheaper/faster model is sufficient since the architecture is already validated and documented in specs/.
Inform the user: "The architecture is fully validated. From Phase 5 onward, you can switch to a faster/cheaper model (e.g., Sonnet instead of Opus) \u2014 the design decisions are persisted in state.json and specs/, so no context is lost.

**HOW TO SWITCH CLEANLY:** Do NOT change the model in the current chat. Mid-conversation switching makes the new (smaller-context) model try to compact the previous session, which destroys the structured context that Versus preserves via MCP. Instead:
1. Close the current chat and open a NEW chat with the target model
2. Type \`retomar Versus\` \u2014 the SessionStart hook recovers state via MCP cleanly (phase, decisions, specs/), no compaction needed
3. The new model starts fresh but with full methodology state"

### Next Step (MANDATORY when all items are \u2705):
1. Display the LLM Switch Point notification (see above).
2. **Ask the user to decide, in chat (R2 format), default "Continue here":**
   - **"Continue here" (Recommended if the current model is already cost-appropriate)** \u2014 stay in this chat for Phase 5
   - **"Switch model"** \u2014 close this chat, open a new one with the target model, type \`retomar Versus\`

   This is a DECISION, not a notice. Do NOT write "I am advancing to Phase 5; interrupt me if you want to switch" \u2014 announcing and proceeding puts the burden of interrupting on the user, at the one moment where the choice is cheapest to make. It is only free BEFORE any code exists: once Phase 5 has written files, switching means abandoning a session mid-implementation.
3. Call advance_phase() to move to Phase 5 \u2014 in BOTH cases. Phase 4's gate is already satisfied; a new session should resume at Phase 5, not re-run the convergence check.
4. If the user chose "Switch model": call record_decision(phase=4, category='process', content='LLM SWITCH: user will resume Phase 5 in a new chat with <model>') and STOP your response. Do not start implementing.
5. If the user chose "Continue here": call get_phase_guidance() and begin Phase 5 implementation immediately: read \`specs/technical/architecture.md\` (the Phase 1 artifact) for the first module \u2014 its interface, dependencies and assumptions \u2014 then consult the rest of specs/ and start coding. Work from the persisted doc, not chat recall.`;
var PHASE_5_GUIDANCE = `## Phase 5 \u2014 Code Implementation
### Verification: Automated-AV (compile, lint, type check) | Dedicated session per module

### Decoupled session principle:
Each module must be implementable in an independent session. Required context: architecture document (~2k tokens) + module interface + relevant specs/. If more is needed \u2192 insufficient granularity (return to P1).
**CAUTION AP3 (Monolithic session).**

### If starting in a NEW SESSION (LLM Switch or resumed project):
The methodology is context-safe: all decisions persist in state.json, all specs in specs/. To recover context:
1. Call get_decisions() \u2014 all architecture, patterns, scope, and P3 decisions.
2. Call check_specs_status() \u2014 which spec directories are populated.
3. Read populated specs/ (specs/technical, specs/models, specs/design).
In a CONTINUOUS session (P0\u2192P5 without interruption), the conversation context already holds all decisions \u2014 proceed directly to modules.

### BEFORE each module, consult:
- specs/technical (algorithm, formulas, params)
- specs/examples (reference code)
- specs/references (original paper)
- specs/datasets (test data)
If numerical parameters without values in specs/ \u2192 STOP and research. Reference source in code.
**CAUTION AP7 (Coding without reference).**

### Binding Constraints from P1/P3 (MUST be respected before writing any code):
The technology stack, patterns, and negative scope decided in P1 (and revised in P3) are HARD CONSTRAINTS. Before coding any module, confirm:
- Tech stack: use ONLY the languages, runtimes, and frameworks explicitly selected in P1.
- Patterns: apply ONLY the architectural patterns chosen. Do not import new patterns.
- Negative scope: do NOT implement anything listed as out-of-scope.
If unsure, check get_decisions(phase=1) \u2014 never assume or default to a familiar tech.

### Apply S6 (Tier 1/2/3) per module:
- Tier 1: Does a mature lib exist AND was it approved in P1? \u2192 USE IT. New code = UI + integration + glue.
- Tier 2: Documented algorithm with ref? \u2192 PORT literally (same structure, same names, test against same inputs).
- Tier 3: Neither of the above. If complex domain \u2192 deposit logic in specs/technical before coding.

### Checklist per module: mature lib? \u2192 if not, why? \u2192 documented algorithm? \u2192 portable implementation? \u2192 decision with record_decision().

### Apply S7 (Discipline):
After each module: run adversarial micro-check \u2014 ask "Where does this implementation DIVERGE from specs/?" Find differences, do NOT validate (AP1 risk: the agent wrote the code and is biased toward \u2705). Fix any divergence before starting the next module.
Do NOT write text between modules \u2014 the next tool call must be the first tool call of module X+1. Do NOT ask permission between modules. Only stop for actual decisions (ambiguity, blocker, Tier choice).

### S6 alarm signal (immediate STOP):
If creating heuristics for problems with known solutions, debugging complex logic written from scratch, doing trial-and-error on something deterministic, or spending >2 iterations on the same module \u2192 STOP, communicate, seek reference implementation (Tier 2).

### S6 loop detection \u2014 what actually trips it (P5-P6):
What S6 forbids is **blind debugging**: re-running the tests hoping something sticks, without a named cause. It does NOT forbid debugging. Four failures with four named causes is the normal cycle; four failures with no cause named is the loop.

The runtime rule, enforced by hooks:
- Only a **FAILED** test run counts. A passing run clears the counter \u2014 final verification (S4) is therefore never blockable. Test-running is the job in P6, not the offense.
- ${LOOP_FAILURE_THRESHOLD} consecutive failures **with no diagnosis recorded between them** \u2192 the next test run is BLOCKED.
- The escape is to name the cause: \`record_decision(phase=<5|6>, category='diagnosis', content='<root cause + the fix it implies>')\`. This clears the counter immediately. Categories 'diagnosis', 'bugfix' and 'root-cause' all count.
- Fix a test, name why it broke, run again \u2014 the counter never accumulates and you are never blocked.

Do this because it is the honest record of the debugging session, not to appease the hook: if you cannot state the root cause in one sentence, you do not have one, and that is precisely the moment S6 exists to catch. An empty ritual diagnosis defeats the safeguard and only fools you.

If S6 blocks you and you genuinely cannot name a cause: that IS the finding. Go to Tier 2 \u2014 find a reference implementation, consult specs/technical/ and specs/examples/, reconsider the approach, and record THAT as the diagnosis.

### Original Scope Adversarial Review (MANDATORY before Scope Inventory \u2014 \u26A0\uFE0F MUST DISPLAY):
Before running the Scope Inventory, the LLM MUST perform an adversarial comparison between what was promised in P0 and what is actually delivered. This is the safeguard against AP10 (silent scope deferral).

**Step 1 \u2014 Recover original commitments:**
- Call get_decisions(phase=0) to retrieve Delivery Target, Success Criteria, Out of Scope items
- Read the P0 Production Capacity Check inventory (asset table from Phase 0)
- Read specs/validation for acceptance criteria

**Step 2 \u2014 Build the Promise vs Delivery table (\u26A0\uFE0F MUST DISPLAY):**

| Item promised in P0 | Delivered? | Status |
|---|---|---|
| <literal item from P0 commitments> | <count delivered / count promised> | \u2705 / \u{1F7E1} (partial) / \u274C |

Cover ALL items: scenes/screens, classes/entities, mechanics/features, assets (visual/audio/data), success criteria thresholds, accessibility/performance targets, integrations.

**Step 3 \u2014 Adversarial framing (CRITICAL):**
Operate in GENERATION mode (AP1): "Find every gap. List every promise that is not fully delivered." Do NOT be charitable to your own work. A promise without delivery = \u274C, no exceptions for "non-blocking" or "for next session" \u2014 that is exactly AP10. Partial delivery (e.g., 4/9 scenes) = \u{1F7E1}, not \u2705.

**Step 4 \u2014 User decision via AskUserQuestion (MANDATORY when any \u{1F7E1} or \u274C exists):**

Present the table and ask the user how to proceed:

- **Option 1 \u2014 "Continue Phase 5"**: complete the missing items before advancing. Recommended when gaps are essential to the product.
- **Option 2 \u2014 "Renegotiate scope"**: some \u274C items will not be delivered in this cycle. Will generate \`record_decision(category='scope', content='SCOPE REVISION at P5 exit: <items removed> \u2014 <reason>')\` to re-baseline the Delivery Target before advancing.
- **Option 3 \u2014 "Advance accepting gaps as known debt"**: \u274C items remain documented as known technical debt. Will generate \`record_decision(category='constraint', content='ACCEPTED GAPS at P5 exit: <list> \u2014 to be addressed in cycle v2 via start_new_cycle')\` documenting the conscious deferral.

**No default. No silent path.** The user MUST choose.

**Branching:**
- Option 1 \u2192 return to module implementation, do NOT proceed to Scope Inventory
- Option 2 \u2192 call record_decision(scope), THEN proceed to Scope Inventory
- Option 3 \u2192 call record_decision(constraint), THEN proceed to Scope Inventory

**CAUTION AP10:** Without this review, gaps get silently deferred via prose in mark_exit_criterion details. With this review, every deferral is explicit, recorded, and consented by the user. AP10 only fires against silent deferral; documented deferral via record_decision is legitimate scope management.

---

### Scope Inventory (MANDATORY before advance_phase \u2014 \u26A0\uFE0F MUST DISPLAY):
After all modules are implemented AND Original Scope Review was completed (with user decision recorded), before calling advance_phase():
1. **P1 modules present?** List every module defined in the P1 decomposition \u2014 \u2705 if present in codebase, \u274C if missing.
2. **specs/validation covered?** List every requirement in specs/validation \u2014 \u2705 if covered by at least one module, \u274C if not.
3. **UI runnable \u2014 empirical proof, not prose?** If the project has a UI module (listed in P1 decomposition): you MUST ask the user via AskUserQuestion to execute AT LEAST ONE Phase 0 use case end-to-end and report whether it worked. Only mark met=true if user explicitly confirms. The \`details\` field MUST contain the user's literal confirmation, e.g. "User executed UC-1 (login\u2192dashboard) and confirmed it works". For backend-only: mark_exit_criteria(phase=5, criterion='ui_runnable', met=true, details='N/A \u2014 backend-only, no UI module in P1').

**CAUTION AP10 (Silent scope deferral):** Marking ui_runnable as met=true with prose like "UI rendered but content missing" or "engine works but assets pending" is forbidden. If the use case from P0 cannot be executed end-to-end by a human, the criterion is met=false. Either: (a) complete the missing pieces before advancing, OR (b) renegotiate the Delivery Target via record_decision(category='scope').

Scope inventory = **presence/absence check** (not quality \u2014 that is Phase 6's job) AND **empirical use-case validation** (not just file existence).
If any \u274C: implement the missing module/requirement before advancing.
**CAUTION AP1:** do NOT mark \u2705 without checking \u2014 the goal is to find \u274Cs, not to confirm \u2705s.

### Next Step (MANDATORY \u2014 do NOT stop after scope inventory):
When scope inventory is all \u2705: call advance_phase() to move to Phase 6. Then call get_phase_guidance() and begin Phase 6 testing immediately.`;
var PHASE_6_GUIDANCE = `## Phase 6 \u2014 Tests
### Verification: Automated-AV (unit tests, integration) + Human-AV (manual exploratory testing)

### S4 \u2014 Explicit Verification: NEVER assume tests passed. Always execute and verify output.
**CAUTION AP5 (Absence of human-AV):** Automated tests verify formalizable properties. Semantic adequacy, usability, and domain correctness REQUIRE human judgment.

### Step 0 \u2014 Session Renewal (RECOMMENDED before testing):
Testing your own code with the same context that wrote it activates confirmation bias ("of course it works, I just wrote it"). Recommend the user start a fresh chat session before Phase 6 to decouple implementer from tester (S4 spirit, automated form).

Use AskUserQuestion with the following options (default: "New session"):
- **"New session"** \u2014 exit current chat, open a new one (also the right moment to switch models if desired, e.g., test execution does not need Opus capabilities), type \`retomar Versus\` to recover state, then resume Phase 6
- **"Continue here"** \u2014 proceed in current session (faster but less rigorous; may miss issues the implementer didn't anticipate)

If user picks "New session": call record_decision(phase=6, category='testing', content='SESSION RENEWAL: user will return in new chat \u2014 recover with retomar Versus') and STOP your response. The user will resume.
If user picks "Continue here": proceed to Step 1.

### Step 1 \u2014 Spec-Driven Test Protocol (MANDATORY before writing any test):
Test against SPECS, not against implementation. The code you wrote is suspect \u2014 the specs are the source of truth.

**1.1. Recover scope:**
- Call get_decisions(phase=0) \u2192 list ALL use cases
- Read specs/validation \u2192 list ALL validation criteria
- Read specs/technical \u2192 list ALL technical constraints

**1.2. Build the Test Map (\u26A0\uFE0F MUST DISPLAY):**
For EACH spec item, declare:
| Spec | Test | Verifies | Type |
|------|------|----------|------|
| UC-1: User login | test_login_valid_credentials | Correct redirect + session created | Positive |
| UC-1: User login | test_login_invalid_password | Error message shown, no session | Negative |
| VAL-3: Response < 200ms | test_search_response_time | Measures actual response time against 200ms threshold | Positive |

Rules:
- Every use case from Phase 0 \u2192 at least 1 positive + 1 negative test
- Every criterion from specs/validation \u2192 at least 1 test that verifies the EXACT criterion (not a proxy)
- Every constraint from specs/technical \u2192 at least 1 test within documented ranges
- Minimum ratio: 1 negative test for every 2 positive tests

**1.3. Distinguish "test green" from "spec met":**
A passing test only validates a spec if it verifies the EXACT criterion. Examples of FALSE coverage:
- Spec says "< 200ms" \u2192 test checks "returns results" (no timing) \u2192 spec NOT verified
- Spec says "supports 100 concurrent users" \u2192 test checks single user \u2192 spec NOT verified
- Spec says "error message is user-friendly" \u2192 test checks error is thrown \u2192 spec NOT verified

### Step 2 \u2014 UI Testing Tooling (only if P1 declared a UI module):
Check P1 decisions and projectSpec for a UI module. If present, before implementing tests, propose appropriate automation tooling:

1. Identify project stack (read get_phase_state().projectSpec.stack and Phase 1 decisions)
2. Match to a tooling category and present 2-3 options via AskUserQuestion (mark recommended) plus an "Other" option for the user to specify:

| Stack | Recommended | Alternatives |
|---|---|---|
| Web SPA | Playwright | Puppeteer, Cypress |
| React Native | Detox | Maestro |
| Electron | Playwright (with electron support) | Spectron |
| CLI | bats | expect |
| Mobile native | Maestro | Appium, XCUITest |

3. Install the chosen tool and write at least ONE smoke test exercising the primary user flow before regular spec-driven tests.
4. Record decision: record_decision(phase=6, category='testing', content='UI TOOL: <chosen> \u2014 <rationale>')

If P1 declared no UI module, skip this step. Proceed to Step 3.

### Step 3 \u2014 Write and Execute Tests:
- specs/datasets \u2192 test against ground truth (if empty, generate synthetic data and deposit in specs/datasets)
- Execute ALL tests. Read output carefully. Fix failures before proceeding.
- After all automated tests pass, run the actual application/artifact and verify behavior end-to-end.

### Step 4 \u2014 Record Spec Coverage (MANDATORY):
Record the coverage checklist as a persistent, traceable decision:
record_decision(phase=6, category='spec-coverage', content='SPEC COVERAGE REPORT: ...')

The content MUST follow this structure:
- COVERED: [list of spec items with their test names and result]
- NOT COVERED: [list of spec items not testable automatically + justification]
- NEGATIVE TESTS: [count positive / count negative / ratio]
- GAPS: [any spec where test exists but does NOT verify the exact criterion]

### Step 5 \u2014 Manual Exploratory Testing (MANDATORY before Phase 7):
**Important: manual testing MUST be performed by the human user, not simulated by the AI.**
The AI cannot replicate real user interactions. After automated tests pass:
1. Present the test plan to the user: list the Phase 0 use cases they must execute and the edge cases to test.
2. Record the testing status with record_decision(phase=6, category='testing') BEFORE the user leaves.
3. Wait for the user to return with their test results. Do NOT mark manual_testing as met or advance to Phase 7 before the user reports results.

What the user must test:
- Start the application
- Execute each Phase 0 use case as an end user
- Test edge cases: rapid/double clicks, empty inputs, interruptions, timeouts
- Evaluate feedback: are messages understandable? Non-technical errors? Actionable results?
- Document and report issues back to this session

Both (automated + manual) are mandatory gates. Neither replaces the other.

### Multi-Session Testing Protocol:
Manual testing often spans multiple sessions (user tests outside Claude, returns with feedback).
To maintain continuity across sessions:

**BEFORE the user leaves to test (\u26A0\uFE0F MUST DISPLAY testing status summary in chat):**
Record a testing decision summarizing the current state:
record_decision(phase=6, category='testing', content='TESTING STATUS: ...')
The content MUST use this structure:
- Line 1: TESTING STATUS: [automated-pending | automated-done | manual-in-progress | manual-done]
- Line 2: PASS: [list of what passed] (or "none yet")
- Line 3: FAIL: [list of known issues] (or "none")
- Line 4: NEXT: [what to test next / what user should focus on]

**WHEN the user returns with test feedback:**
1. Call get_decisions(phase=6) to recover ALL Phase 6 testing decisions
2. Read the most recent testing-category decisions to reconstruct context
3. Record the user's feedback as a new testing decision
4. Update exit criteria based on feedback (mark_exit_criterion for manual_testing, edge_cases)
5. If issues found: fix them, then record updated status

**WHEN fixing issues from manual testing:**
After each fix, record a testing decision noting: what was fixed, what still needs retesting.
This ensures the NEXT session knows exactly what changed since the last test round.

### Next Step (MANDATORY when all testing is complete):
Both automated and manual testing must be done before advancing. When both gates are \u2705: call advance_phase() to move to Phase 7. Then call get_phase_guidance() and begin Phase 7 post-review immediately.

**tests_passing is engine-witnessed, not asserted (S4).** advance_phase() to Phase 7 is BLOCKED unless the test-outcome hook actually saw a GREEN run during Phase 6 \u2014 marking tests_passing met is not enough. Run the full suite here (a recognized command: npm test, jest, pytest, cargo test, go test, \u2026) and let it pass. If you switched sessions/models at Step 0, run the suite again in this session so the engine witnesses it. The engine checks that the run was green, not that the tests are adequate \u2014 coverage and meaningfulness are your and the user's judgment.`;
var PHASE_7_GUIDANCE = `## Phase 7 \u2014 Post-Review
### Verification: Human-AV (operator confirms product works and captures project lessons)

### Step 1 \u2014 Update specs/:
- specs/validation \u2192 actual results (expected vs obtained)
- specs/technical \u2192 final decisions, discarded algorithms and why
- specs/references \u2192 references discovered during implementation

### Step 2 \u2014 Product evaluation (\u26A0\uFE0F MUST DISPLAY in chat):
Ask the user via AskUserQuestion: does the software meet the P0 requirements? What was missed? Any pending issues to carry into v2?

### Step 3 \u2014 Project lessons (\u26A0\uFE0F MUST DISPLAY as list in chat):
Capture 3-5 lessons about THIS project (not about the methodology):
- Domain insights that emerged during implementation (edge cases, invariants, constraints discovered)
- Tech stack pitfalls encountered (library quirks, integration gotchas, performance surprises)
- Patterns that worked / didn't work for this project's specific constraints
- Assumptions from P0/P1 that turned out wrong

Write the lessons to \`specs/references/lessons.md\` \u2014 the persisted record that feeds the next cycle. start_new_cycle() is BLOCKED until \`specs/references/lessons.md\` exists and is non-trivial; marking lessons_documented met is not enough. This is what lets a v2 (or a post-mortem) actually read what this cycle learned instead of it vanishing with the chat.

### Meta-iteration v1.0 \u2192 v2.0 (\u26A0\uFE0F MUST DISPLAY offer in chat):
After completing all Phase 7 steps, you MUST offer the user the option to start a new development cycle via AskUserQuestion:
- Option 1: "Start v2.0 cycle" \u2014 calls start_new_cycle() to reset to Phase 0 while preserving all context
- Option 2: "Project complete" \u2014 no further action, methodology concludes

If the user chooses to start a new cycle:
1. Call start_new_cycle() \u2014 this preserves decisions, projectSpec, history, and specs/
2. specs/ from the previous cycle is the BASELINE \u2014 knowledge is NOT lost between cycles
3. Phase 0 of the new cycle starts from existing specs/ (doesn't restart from zero)
4. Previous decisions (get_decisions) serve as context \u2014 what was discarded and why
5. Negative scope from the previous cycle can become new scope (with operator approval)
6. Phase 7 lessons feed into the new cycle's process
7. **REVERSE LLM SWITCH \u2014 a decision, not a notice (when start_new_cycle returns \`_modelSwitchAction\`):** The new cycle starts at Phase 0 (design), which needs the MOST CAPABLE model (e.g., Opus). If the user switched to a code-execution model (e.g., Sonnet) at the previous cycle's P4\u2192P5 switch, they are likely still on it. Display the recommendation from the \`_modelSwitchAction\` field, then **ask the user to decide in chat (R2 format):**
   - **"Switch model" (Recommended \u2014 Phase 0 design benefits from the most capable model)** \u2014 close this chat, open a new one with the design-grade model, type \`retomar Versus\`
   - **"Continue here"** \u2014 proceed with Phase 0 on the current model

   This is a DECISION, not a notice. Do NOT display the recommendation and then load Phase 0 and proceed \u2014 announcing and proceeding puts the burden of interrupting on the user, at the one moment where the choice is cheapest to make (before the new cycle's design work begins).
8. If the user chose "Switch model": call record_decision(phase=0, category='process', content='LLM SWITCH (reverse): user will resume Phase 0 of the new cycle in a new chat with <model>') and STOP your response. Do not load Phase 0 guidance.
9. If the user chose "Continue here": call get_phase_guidance() to load Phase 0 instructions for the new cycle.

IMPORTANT: Do NOT use init_project() for meta-iteration \u2014 that wipes all previous context. Use start_new_cycle() which preserves the knowledge base.`;
var FULL_GUIDANCE = {
  0: PHASE_0_GUIDANCE,
  1: PHASE_1_GUIDANCE,
  2: PHASE_2_GUIDANCE,
  3: PHASE_3_GUIDANCE,
  4: PHASE_4_GUIDANCE,
  5: PHASE_5_GUIDANCE,
  6: PHASE_6_GUIDANCE,
  7: PHASE_7_GUIDANCE
};
function getCompleteGuidance() {
  const parts = [];
  parts.push("## ACTIVE GLOBAL RULES");
  parts.push(GLOBAL_RULES.R1);
  parts.push(GLOBAL_RULES.R2);
  parts.push(GLOBAL_RULES.R5);
  parts.push("R4 (per-phase timing):");
  for (const [p, r4] of Object.entries(GLOBAL_RULES.R4_TIMING)) {
    parts.push(`  Phase ${p}: ${r4}`);
  }
  parts.push("");
  parts.push(ACTIVATION_TRIGGERS);
  parts.push("");
  parts.push(ANTIPATTERNS);
  for (let p = 0; p <= 7; p++) {
    const phaseGuidance = FULL_GUIDANCE[p];
    if (phaseGuidance) {
      parts.push("");
      parts.push(phaseGuidance);
    }
  }
  return parts.join("\n");
}

// src/hooks/inject-context.ts
function main() {
  const workspacePath = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const engine = new StateEngine(workspacePath);
  const state = engine.getPhaseState();
  if (!state) {
    process.exit(0);
  }
  const phase = state.currentPhase;
  const phaseName = getPhaseDefinition(phase)?.name ?? "Unknown";
  const lines = [
    `[Versus] Phase ${phase} \u2014 ${phaseName} | Iteration ${state.currentIteration}`
  ];
  if (phase < 7) {
    const phaseCriteria = engine.getExitCriteriaWithDefs(phase);
    const allMet = phaseCriteria.length > 0 && phaseCriteria.every((c) => c.met);
    if (allMet) {
      lines.push(`\u26A0\uFE0F READY TO ADVANCE \u2014 Phase ${phase} exit criteria are ALL met. Your VERY NEXT tool call MUST be advance_phase() followed by get_phase_guidance(). Do NOT write summary text. Do NOT wait for user input. Continue work into Phase ${phase + 1} in the same turn.`);
    }
  }
  if (state.phase0Score !== null) {
    lines.push(`Score Phase 0: ${state.phase0Score}/100`);
  }
  if (state.decisions.length > 0) {
    const byPhase = {};
    for (const d of state.decisions) {
      if (!byPhase[d.phase]) byPhase[d.phase] = [];
      byPhase[d.phase].push(d);
    }
    lines.push("Decision history (all phases):");
    for (const p of Object.keys(byPhase).map(Number).sort((a, b) => a - b)) {
      for (const d of byPhase[p]) {
        lines.push(`  [P${d.phase}/${d.category}] ${d.content}`);
      }
    }
  }
  const spec = state.projectSpec;
  if (spec) {
    if (spec.stack.length > 0) lines.push(`Approved stack: ${spec.stack.map(specEntryValue).join(", ")}`);
    if (spec.outOfScope.length > 0) lines.push(`Out of scope: ${spec.outOfScope.map(specEntryValue).join(", ")}`);
    if (spec.patterns.length > 0) lines.push(`Patterns: ${spec.patterns.map(specEntryValue).join(", ")}`);
    if (spec.constraints.length > 0) lines.push(`Constraints: ${spec.constraints.map(specEntryValue).join(", ")}`);
  }
  if (phase === 2) {
    const hasLensDecision = (state.activatedLenses?.length ?? 0) > 0 || state.decisions.some((d) => {
      const up = d.content.toUpperCase();
      return up.includes("ACTIVATED LENSES") || up.includes("LENTES ATIVADAS");
    });
    if (!hasLensDecision) {
      lines.push("\u26A0 P2 STEP 1 MISSING: No lens activation on record. Call record_activated_lenses(conditional=[...], notActivated=[{lens, reason}, ...]) \u2014 the structured tool \u2014 BEFORE applying any lens.");
    }
  }
  if (phase < 5) {
    lines.push("RESTRICTION: Phases 0-4 \u2014 DO NOT implement code. Use the MCP tools to manage the methodology.");
  }
  lines.push(getCompleteGuidance());
  const loop = engine.getLoopCounter();
  if (loop.count >= LOOP_FAILURE_THRESHOLD - 1) {
    const blocked = loop.count >= LOOP_FAILURE_THRESHOLD;
    lines.push(
      `\u26A0 S6: "${loop.pattern}" failed ${loop.count}x in a row with no diagnosis recorded (threshold: ${LOOP_FAILURE_THRESHOLD}).` + (blocked ? ` Test runs are BLOCKED. Name the cause: record_decision(category='diagnosis', content='...') \u2014 that clears it.` : ` Record the root cause with record_decision(category='diagnosis') before the next run.`)
    );
  }
  process.stdout.write(lines.join("\n") + "\n");
  process.exit(0);
}
main();
