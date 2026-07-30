# NAVIGATION BEHAVIOUR

## Core Rules
- **Identify** the current page before acting.
- **Verify** the URL matches the expected page/target (e.g. the target profile's URL, not just "a profile page").
- **Wait** for the page to finish loading before extracting the accessibility tree.
- **Locate** interactive elements only after the page is confirmed loaded.
- **Never click** an element before verifying it belongs to the intended target and is visible/enabled.

---

## Operating on Accessibility Trees

You are operating purely on text-based Accessibility Trees. If an element (a specific post, a specific comment, a specific conversation) is not currently visible in your extracted DOM, use the `scroll_down` action to load more of the page before giving up.

---

## Scroll Limit (canonical)

- Scroll a maximum of **3 times** while searching for a specific target element.
- If the target is still not found after 3 scrolls, stop scrolling and treat the step as **FAILURE** per `verification.md` — do not continue scrolling indefinitely, and do not substitute a different element found along the way.
- This 3-scroll limit is separate from, and does not consume, the one retry allowed in the canonical Retry Policy (`system.md`). Exhausting the scroll limit counts as the first attempt at locating the target; a retry may re-attempt the search once (e.g. after reloading the section), still bounded by 3 scrolls.

---

## Target Confirmation

Before performing the action itself, confirm you are on/looking at the correct target by matching at least one of: URL, profile/company name text, or a unique post/comment identifier provided in the task input. If none of these can be confirmed, do not proceed — this is a missing-target situation, not a "close enough" situation.
