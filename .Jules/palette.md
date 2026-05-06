## 2024-05-23 - Status Tag Alignment
**Learning:** Terminal output alignment depends on strict character counts. `[ OK ]` (green) is 6 chars. `[FAIL]` (red) is 6 chars. `[SKIP]` (yellow) must also be 6 chars to maintain vertical alignment of the resource list.
**Action:** When adding new status tags or modifying existing ones, ensure the visible character count (excluding ANSI codes) is exactly 6.
