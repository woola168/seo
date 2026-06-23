Code review only. Do not edit files.

Review the current uncommitted changes in this repository, including tracked diffs and untracked files under apps/geo-analysis-api and packages/geo-analysis-*.

Apply the inherited AGENTS.md rules and the current user requirement that code comments/docstrings should be written in Traditional Chinese while identifiers and established technical terms may remain English.

Prioritize actionable issues only:
- correctness or behavioral regressions
- API/schema compatibility
- authorization/security
- persistence and database mapping problems
- data-loss risk
- error handling problems
- missing tests for risky behavior

Do not report style-only, naming-only, or docstring-only issues unless they violate a current explicit requirement or affect generated API schema meaningfully.
Do not edit any product file.

Write the report to C:\Users\TPP06792\Documents\younilab-seo\tmp\agy_current_diff_review_result_ascii.md using English ASCII only to avoid encoding issues.
Return at most 6 findings, ordered by severity. Each finding must include exact current file path and line number, impact, and concise fix.
If there are no actionable findings, write NO_FINDINGS and list residual test gaps.
After writing the result file, reply exactly: AGY_CURRENT_DIFF_REVIEW_DONE
