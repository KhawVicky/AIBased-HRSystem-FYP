import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (file) => readFile(new URL(`../${file}`, import.meta.url), "utf8");

const run = async () => {
  const [mapper, list, globalList, breakdown, api] = await Promise.all([
    read("app/lib/candidateData.ts"),
    read("app/components/candidates/CandidateList.tsx"),
    read("app/components/candidates/NewCandidates.tsx"),
    read("app/components/candidates/CandidateScoreBreakdown.tsx"),
    read("server/api.php"),
  ]);

  for (const field of [
    "parsedProfile",
    "scoreBreakdown",
    "weightedContribution",
    "matchedResumeEvidence",
    "analysisStatus",
    "eligibilityReasons",
    "filteredOut",
  ]) {
    assert.match(mapper, new RegExp(field), `mapper must preserve ${field}`);
  }

  assert.match(list, /apiFetch<\{/);
  assert.match(list, /`\/jobs\/\$\{jobId\}\/candidates`/);
  assert.match(list, /mapApiCandidate/);
  assert.match(list, /Parsed Resume Profile/);
  assert.match(list, /getEligibilityStatusLabel/);
  assert.match(list, /Resume analysis failed\. No parsed profile was persisted\./);
  assert.match(list, /Resume profile is pending analysis\./);
  assert.doesNotMatch(list, /Math\.random|createObjectURL|recalculateRanks|renderSummary/);
  assert.doesNotMatch(
    list,
    /This candidate has been evaluated by the system and is ready for HR review/,
  );

  assert.match(globalList, /apiFetch<\{ applications: Application\[\] \}>\("\/applications"\)/);
  assert.match(globalList, /\/jobs\/\$\{applicant\.jobId\}\/candidates\?applicationId=/);
  assert.match(globalList, /getAnalysisStatusLabel/);
  assert.match(globalList, /getEligibilityStatusLabel/);

  assert.match(breakdown, /item\.matchedEvidence/);
  assert.match(breakdown, /item\.weightedScore/);
  assert.match(breakdown, /No matching resume evidence was persisted/);
  assert.match(mapper, /matchLevel: item\.matchLevel \|\| "none"/);
  assert.match(mapper, /case "pending"/);
  assert.match(mapper, /case "failed"/);
  assert.match(await read("app/components/candidates/CandidateCard.tsx"), /candidate\.filteredOut/);

  assert.match(api, /a\.eligibility_reasons_json AS eligibilityReasonsJson/);
  assert.match(api, /resume\.parsed_profile_json AS profileJson/);
  assert.match(api, /\$candidate\["scoreBreakdown"\]/);
  assert.match(api, /\$candidate\["parsedProfile"\]/);
  assert.match(api, /\$candidate\["filteredOut"\]/);
  console.log("Candidates real-data integration contract passed.");
};

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
