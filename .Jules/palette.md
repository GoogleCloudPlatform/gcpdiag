# Palette's Journal

## 2025-02-18 - [Documentation Accessibility Polish]
**Learning:** Decorative images next to text (like logos in headers) should have empty alt text to avoid redundancy for screen readers. The pattern `[Icon] Text` is common and often implemented with `alt="Icon name"`, which results in "Icon name Text".
**Action:** Audit all logo/icon usages next to text and enforce `alt=""` and `aria-hidden="true"`.
