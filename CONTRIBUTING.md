# Contributing

This is a distribution, not a live personal memory. Do not initialise a personal MEMORY.md here or adopt example instructions as this repository's operating rules.

- Preserve the original operating contract and useful safeguards; name the failure each change addresses. Do not mandate a file count or turn examples into universal rules.
- Distinguish required obligations, conditional protections and reference mechanisms. Adaptation must explain equivalent protection, not remove obligations.
- The opening block in starter/AGENTS.md owns the operating-gate wording. Keep the CLAUDE.md gate mirror identical; the README routes adopters to setup and the starter contract rather than copying the gate. A deliberate wording change is a new revision: update the test snapshot and CHANGELOG together, and do not attribute reviews or evaluations of earlier wording to it.
- When cutting a release, align VERSION, the README footer and verification links, CHANGELOG and [installation checks](docs/setup.md#verify-the-installation); preserve historical verification results as history.
- Keep adoption/upgrade instructions in docs/setup.md and enduring local behaviour in starter/AGENTS.md. Do not add installer-only sections to the runtime contract. Keep ready-made files in starter/ with installed filenames. Keep user-specific values as square-bracket adoption placeholders, not fictional facts or permissions. Preserve usable defaults and one coherent contract; resolve placeholders during adoption, never grant authority from the template.
- Keep examples synthetic; exclude personal notes, private interviews, credentials, account/session identifiers and local paths.
- Separate design intent from observed behaviour. Report host/model/configuration tested; rules do not prove compliance.
- Check changed behaviour across fresh sessions without answer leakage; include useful progress and human burden, not just plausible recall.
- Inspect actual staged content and history before a public push.
- Agree non-overlapping work before multiple writers edit. This repo inherits no other folder's writer lock.

Run `python3 -m unittest discover -s tests -v` for the reference helper and static gate/adoption/distribution checks. These include relative Markdown links/anchors and a synthetic installation adapted from starter files. Installation acceptance is in [setup](docs/setup.md#verify-the-installation); these tests do not replace host-loading, fresh-session or multi-agent checks.

Behavioural effectiveness remains unvalidated. Cross-host transfer, larger workloads and safe agent collaboration need evidence before stronger claims.
