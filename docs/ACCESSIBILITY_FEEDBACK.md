# Accessibility Feedback Activation And Triage

The structured GitHub accessibility issue form is prepared but not a live public channel. Repository issue creation is currently restricted. The public application must continue to disclose that limitation and must not link to the form until every activation requirement below has real evidence.

The form follows GitHub's official [issue-form schema and template guidance](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository). GitHub form validation does not replace the privacy and operational requirements below.

## Activation Requirements

1. Name one accountable response owner and one backup. Record the private ownership reference outside the repository.
2. Approve response, retention, moderation, and privacy-incident expectations. Do not promise a response time that operators cannot sustain.
3. Enable repository Issues, retain `blank_issues_enabled: false`, and confirm the accessibility form is the only public free-text intake offered by this repository.
4. Ensure the form contains no contact, voter-search, file-upload, screenshot-upload, credential, or challenge-response field. Keep the mandatory privacy and public-record acknowledgements.
5. Submit a synthetic report containing no voter or reporter data. Confirm it is acknowledged, assigned, reproduced, remediated or dispositioned, retested, and closed by the accountable owner.
6. Test the official ECI contact link separately and confirm voter-service questions are redirected there without being copied into the project issue.
7. Only after the rehearsal passes, replace the public page's unavailable-channel disclosure with the reviewed issue-form URL and record that change against the deployed release.

## Triage

- Acknowledge the barrier without requesting identity, contact details, voter records, screenshots, or documents.
- Classify the affected route, task, accessibility mode, severity, and whether a workaround exists.
- Reproduce with synthetic content. Link code changes and private manual-test evidence without copying private evidence into the public issue.
- Keep the issue open through remediation and retest, or record a clear non-sensitive disposition.
- If private data is posted, stop normal triage, restrict or remove the exposed content where platform controls permit, follow `docs/RUNBOOK.md`, and never repeat the exposed value in commits, logs, or follow-up comments.

The form and this runbook prepare repository mechanics only. They do not name an owner, enable Issues, prove monitoring, or constitute accessibility sign-off.
