# Gate-check calibration corpus

Frozen copies of **real, unmodified** plans, used by
`tests/test-validate-gate-checks.py` group 9 to calibrate the classification figures in
`scripts/validate-gate-checks.py`'s docstring.

## Why this exists

Group 9 used to calibrate against a live sweep of
`/mnt/vault/Portfolio/ai-tools/coder-plugins/plans/*.md`. That directory grows whenever
anyone authors a plan, so **writing a plan turned the suite red** until four numbers were
hand-edited into a docstring — it fired on three consecutive plans (374/41 → 399/42 →
415/43 → 421/44). And because the vault does not exist on CI, `real` was empty there and
group 9 skipped entirely: the pin had zero CI coverage.

Calibrating against files *in the repo* fixes both. The live-vault sweep is retained, but
only as an informational rate line that cannot fail the suite.

## Why these three files

The classifier has four outcomes, and a corpus that leaves any of them at zero silently
stops testing that branch. These plans were chosen as the smallest set giving every class a
non-zero count, drawn from three different months so the sample is not one author-era:

| File | Source | Copied |
|---|---|---|
| `2026-06-09-i18n-formats-progressive-disclosure-plan.md` | `/mnt/vault/Portfolio/ai-tools/coder-plugins/plans/` | 2026-07-27 |
| `2026-07-14-plan-format-tiering-plan.md` | `/mnt/vault/Portfolio/ai-tools/coder-plugins/plans/` | 2026-07-27 |
| `2026-07-26-backlog-bl020-bl027-plan.md` | `/mnt/vault/Portfolio/ai-tools/coder-plugins/plans/` | 2026-07-27 |

INSTANCE-SHAPED is the constraint that shaped the selection: **of the three files here,
only two carry it** — i18n contributes 1 and plan-format-tiering 2. Both are kept so the
class is not sourced from a single file, where one refresh could silently take it to zero.
The `backlog-bl020-bl027` plan supplies the JUDGMENT and bulk EXECUTABLE counts.

To be precise about how scarce the class actually is, since an earlier draft of this file
got it wrong: a sweep of the vault on 2026-07-27 found **23 INSTANCE-SHAPED checks spread
over 12 of 44 plans**, so substitutes for either file exist. These two were chosen because
they already carried the class among the candidates evaluated — not because they are the
only sources. Swapping one for another vault plan that carries it is legitimate; dropping
to a single source is not.

The existing `portfolio/tests/fixtures/plan-parser/` corpus was evaluated first and
rejected: its 18 files yield 21 checks that are **all PROSE** (0 executable, 0 judgment,
0 instance-shaped). It exercises the plan *parser*, not the gate-check *classifier*.

## What these figures are not

The corpus is representative **in kind, not in proportion**, and the docstring's counts
should not be read as describing the plan corpus at large. Measured 2026-07-27:

| Class | Vault (n=421, 44 plans) | Frozen (n=48, 3 plans) | Skew |
|---|---|---|---|
| EXECUTABLE | 40.6% | 43.8% | +3.1 |
| JUDGMENT | 3.8% | 14.6% | **+10.8** |
| INSTANCE-SHAPED | 5.5% | 6.2% | +0.8 |
| PROSE | 50.1% | 35.4% | **−14.7** |

JUDGMENT is roughly four times over-weighted and PROSE materially under-weighted, because
`backlog-bl020-bl027` was selected for carrying JUDGMENT at all (it contributes 7 of the 7)
and short plans skew away from the prose-heavy tail. That is acceptable for the job this
corpus does — exercising every classifier branch deterministically — and unacceptable for
any claim about how real plans are typically written. If you ever want the latter, sweep
the vault; the informational rate line in the test prints exactly that.

## Rules

- **Copy verbatim.** A hand-trimmed fixture would calibrate the classifier against prose
  nobody actually writes. If a file needs editing to be useful, pick a different file.
- **Refreshing is deliberate, never automatic.** Re-copying a file or adding one changes
  the docstring figures; update them in the same commit and say why in the message. The
  whole point of this directory is that the numbers move only when a human decides they
  should.
- These files are **test data, not documentation**. They are not maintained, not linked
  from the plans index, and their content should not be read as current guidance.
