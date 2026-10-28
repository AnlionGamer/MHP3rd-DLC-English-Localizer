# Version 0.6.3 — Availability-aware wizard

- Page 1 unchanged.
- Page 2 performs a **read-only DLC inventory** and displays detected quest counts plus recognized promotional Palicoes (0–5); no assumption that all five have been downloaded.
- Renamed the all-content option **All recognized installed DLC**. Missing Palicoes appear disabled in individual selection and cannot be installed by the localizer.
- Recruited-Palico option is disabled when no supported promotional Palicoes are selected.
- Page 3 no longer requires a small PPSSPP-closed checkbox; the prominent Apply action and a single final confirmation remain. The existing Windows process check/backup/rollback engine is unchanged. Exceptional partial cases are described and approved in that same confirmation dialog rather than another checkbox.
- Review and partial-approval gate now consider **selected records only**. Unselected unknown/custom Palicoes remain in full diagnostic reports but do not cause irrelevant warnings or prevent quest-only operations.
- Bumped analyzer and patcher metadata to 0.6.3; plan acceptance still requires matching hashes, catalog and options.
- No changes to translation texts, original wide character preservation, or encryption codec. The writer skips unrelated containers entirely when their DLC category is not selected; the safe installation layer is unchanged.
