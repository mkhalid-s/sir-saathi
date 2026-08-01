import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { build } from 'esbuild';

const root = new URL('../', import.meta.url);
const entry = `
  export { states } from './apps/web/src/data/states.ts';
  export { deadlineIsoFor, defaultAnswers, guidanceFor } from './apps/web/src/lib/guidance.ts';
  export { translate } from './apps/web/src/lib/i18n.ts';
`;
const bundle = await build({
  banner: { js: 'import.meta.glob = () => ({});' },
  bundle: true,
  format: 'esm',
  platform: 'node',
  stdin: {
    contents: entry,
    loader: 'ts',
    resolveDir: new URL(root).pathname,
    sourcefile: 'guidance-matrix-entry.ts'
  },
  write: false
});
const temporaryDirectory = await mkdtemp(join(tmpdir(), 'sir-saathi-guidance-'));
const bundlePath = join(temporaryDirectory, 'guidance-matrix.mjs');
let runtime;
try {
  await writeFile(bundlePath, bundle.outputFiles[0].contents);
  runtime = await import(new URL(`file://${bundlePath}`));
} finally {
  await rm(temporaryDirectory, { recursive: true, force: true });
}
const { states, deadlineIsoFor, defaultAnswers, guidanceFor, translate } = runtime;

const situations = [
  'existing_voter',
  'missing_name',
  'new_voter',
  'shifted_address',
  'correction',
  'deceased_family',
  'duplicate_entry',
  'portal_failed'
];
const unavailablePhases = new Set(['schedule_unverified', 'schedule_pending']);
const enumerationPhases = new Set(['pre_enumeration', 'enumeration_open']);
const message = (key) => translate('en', key);

assert.equal(states.length, 36, 'guidance matrix must cover all 36 jurisdictions');
assert.equal(new Set(states.map((state) => state.stateId)).size, 36, 'jurisdiction IDs must be unique');

let caseCount = 0;
for (const state of states) {
  for (const situation of situations) {
    const result = guidanceFor({ ...defaultAnswers, situation }, state, 'en');
    assert.ok(result.title && result.summary, `${state.stateId}/${situation} must produce complete guidance`);
    assert.ok(result.actions.length > 0 && result.documents.length > 0, `${state.stateId}/${situation} must remain actionable`);
    const deadline = deadlineIsoFor(state, situation);
    if (unavailablePhases.has(state.currentPhase)) {
      assert.equal(deadline, undefined, `${state.stateId}/${situation} must not infer a deadline`);
    } else {
      assert.match(deadline ?? '', /^\d{4}-\d{2}-\d{2}$/, `${state.stateId}/${situation} must use a governed deadline`);
    }
    caseCount += 1;
  }

  const normal = guidanceFor(defaultAnswers, state, 'en');
  const staleEnumeration = guidanceFor({
    ...defaultAnswers,
    bloVisited: 'no',
    enumerationFormReceived: 'yes',
    enumerationFormSubmitted: 'no'
  }, state, 'en');
  if (enumerationPhases.has(state.currentPhase)) {
    assert.equal(staleEnumeration.priority, 'high', `${state.stateId} must act on enumeration answers while actionable`);
    assert.equal(staleEnumeration.actions[0], message('guidance.existing.submit_received'));
  } else {
    assert.deepEqual(staleEnumeration, normal, `${state.stateId} must ignore stale enumeration answers outside enumeration`);
  }

  const missingCurrentRoll = guidanceFor({ ...defaultAnswers, currentRollFound: 'no' }, state, 'en');
  assert.equal(missingCurrentRoll.priority, 'urgent', `${state.stateId} missing current-roll entry must be urgent`);
  assert.equal(missingCurrentRoll.title, message('guidance.existing.title_missing'));
  assert.equal(missingCurrentRoll.actions[0], message('guidance.existing.urgent_missing'));

  if (state.currentPhase === 'final_roll_published') {
    assert.equal(normal.summary, message('guidance.existing.summary_complete'));
    assert.equal(normal.actions[0], message('guidance.existing.check_final'));
  }
  if (unavailablePhases.has(state.currentPhase)) {
    assert.equal(normal.summary, message('guidance.existing.summary_unverified'));
    const missingName = guidanceFor({ ...defaultAnswers, situation: 'missing_name', baseRollFound: 'yes' }, state, 'en');
    assert.ok(!missingName.actions.includes(message('guidance.missing.base_reference')));
  }

  const newVoter = guidanceFor({ ...defaultAnswers, situation: 'new_voter' }, state, 'en');
  assert.ok(newVoter.actions.includes(message('guidance.new.track')), `${state.stateId} new-voter guidance must include tracking`);
}

const scheduledExample = states.find((state) => state.finalRollDateIso && state.claimsEndIso && state.enumerationEndIso);
assert.ok(scheduledExample, 'phase matrix requires one complete governed schedule');
const phaseVariants = [
  'pre_enumeration',
  'enumeration_open',
  'pre_draft_publication',
  'claims_and_objections_open',
  'claims_disposal',
  'final_roll_published',
  'schedule_pending',
  'schedule_unverified'
];
for (const currentPhase of phaseVariants) {
  const state = { ...scheduledExample, currentPhase };
  const normal = guidanceFor(defaultAnswers, state, 'en');
  const adversarial = guidanceFor({
    ...defaultAnswers,
    bloVisited: 'no',
    enumerationFormReceived: 'yes',
    enumerationFormSubmitted: 'no'
  }, state, 'en');
  if (enumerationPhases.has(currentPhase)) {
    assert.equal(adversarial.priority, 'high', `${currentPhase} must honor enumeration answers`);
    assert.equal(adversarial.actions[0], message('guidance.existing.submit_received'));
  } else {
    assert.deepEqual(adversarial, normal, `${currentPhase} must ignore enumeration answers`);
  }
  if (currentPhase === 'final_roll_published') {
    assert.equal(normal.summary, message('guidance.existing.summary_complete'));
    assert.equal(normal.actions[0], message('guidance.existing.check_final'));
  }
  if (unavailablePhases.has(currentPhase)) {
    assert.equal(deadlineIsoFor(state, 'existing_voter'), undefined);
    assert.equal(normal.summary, message('guidance.existing.summary_unverified'));
  }
}

console.log(JSON.stringify({
  cases_checked: caseCount,
  jurisdictions_checked: states.length,
  passed: true,
  phase_variants_checked: phaseVariants.length,
  situations_checked: situations.length
}, null, 2));
