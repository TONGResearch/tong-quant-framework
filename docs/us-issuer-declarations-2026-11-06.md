# US Issuer Declaration Review

Date: November 6, 2026, Malaysia time. WP-LAUNCH-001 remains ready, not accepted.
This advances the US-first November 30 target's identity-evidence gap; it does
not complete financial policy, R2 qualification, validation or deployment.

## Implemented Boundary

`read_sec_issuer_claims` in `data.sec_filing_inputs` compares a requested US
symbol with exact ticker declarations inside a retained SEC submissions envelope.
It reuses `read_sec_filing_inputs` and the existing artifact/registry/completed-
batch reconstruction, inside one read snapshot. No new provider, capture,
canonical Instrument, database table, migration or financial alias is created.

The receipt binds the catalog input hash, selected evidence/envelope, normalization
version, actual capture availability, cutoff and exact observed declarations.
Name, tickers and exchanges are unqualified source statements. Unsupported or
missing declarations remain separate states; original payloads remain retained.
Ticker lists are bounded and checked as a whole. Duplicates are not deduplicated;
unsupported siblings cannot leave a favorable partial match. Case, punctuation,
name similarity and ticker/share-class aliases are never normalized or inferred.
Exchange arrays are retained separately: no positional ticker/exchange mapping.

States distinguish CATALOG_UNAVAILABLE, REJECTED_OR_AMBIGUOUS,
TICKER_DECLARATION_MISSING, TICKER_DECLARATION_NULL, NO_DECLARED_TICKERS,
INVALID_TICKER_DECLARATIONS, AMBIGUOUS_TICKER_DECLARATIONS,
TICKER_NOT_DECLARED and TICKER_DECLARED_UNVERIFIED.
Absence is not proof of delisting, non-equity status or historical ticker absence.
A declared ticker is not verified equity identity, source truth or share-class
equivalence. Freshness stays UNASSESSED, trust LOW and precision retrieval_time.
Historical identity, score, replay, validation and execution authorities stay false.

## Entry And Compatibility

The existing `inspect_global_technical.py` accepts optional `--sec-identity` only
with the explicit US read-only SEC database/CIK/accession options. Add this flag
to the retained-sample command in the US delivery plan. It creates no report or
queue and never requests the network. The review and body/catalog/concept reads
share the SEC database snapshot; separate price databases still share only cutoff.

Only this opt-in changes the combined display version to
`US_SEC_IDENTITY_DISPLAY_VERSION`; the previous SEC v1 and no-SEC paths remain
unchanged. `SEC_ISSUER_CLAIMS_VERSION` identifies the derived declaration receipt,
not a new source normalization. Existing SEC v1/v2 capture records remain intact.
The combined pairing status remains CALLER_SELECTED_UNVERIFIED even on a match;
consumers must inspect declaration failures/mismatches, not promote the flag.

## Verification

Focused SEC catalog/body checks: 187 passed, including 40 new cases. They cover
exact match, mismatch, case/punctuation, duplicate/unsupported/empty/null/missing
declarations, separate exchange arrays, actual UTC, no writes, old hashes,
latest failure/tie/tamper/future-completion, file tampering after the catalog read,
competing SQL writer snapshot consistency and opt-in CLI authority boundaries.
Full suite: **3393 passed / 6 skipped**, 205.30 seconds. Ruff, mypy (307 files),
governance (161 checks), git diff --check and scoped security/import review pass.
The three touched runtime modules have no execution/broker/order/trade/fill/
paper/portfolio/notification imports. Skipped external-network tests are not
provider access or source qualification. Checks cover this mixed working tree,
not an exact publishable candidate or an independent strategy validation.

Existing retained MSFT at `2026-10-27T15:25:57.208239+00:00` declares ticker MSFT
and exchange Nasdaq. Result is TICKER_DECLARED_UNVERIFIED, not a current market
or historical share-class assessment. The co-display still includes 706 daily
observations and the unqualified filing; no capture or real database write occurs.
Both sample database hashes remain unchanged across repeated reads.

- Issuer-claim receipt hash:
  `03bf0f3067efb000f2b5e5af5b4516a8494414dbda3ae6cd7c8bada8dc40477a`.
- Opt-in v2 combined display hash:
  `940d8676cfd74345466e2e50d5f2faaeccefc2028dacd4e1d5d07c1a6bbcbe93`.
- Previous SEC v1 combined display hash remains exactly
  `1865f2f15955e4bffb5c9abb9707f1065b52041954d3b2803ed00cb1042cdab7`.

No credentials, remote bodies or private contact headers were fetched or logged.
These public-sample content hashes are consistency receipts, not authentication
or independent source truth. No index/history changes or GitHub synchronization.

## Remaining Work

Source declaration matching does not independently establish security identity,
listing/share-class history, current tradability, adjustment continuity or latest
issuer disclosures. US source-bound fiscal period/accounting/sector contracts,
admitted financial policy, real screening/research, strategy validation and
reviewed deployment/recovery remain outstanding. No deadline, code test or SEC
declaration waives these gates. PIT remains UNSUITABLE; production NOT_READY;
execution and notification defaults remain disabled. No commit or push.
