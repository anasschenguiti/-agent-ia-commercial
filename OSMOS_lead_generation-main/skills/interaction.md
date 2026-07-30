# INTERACTION BEHAVIOUR

## Macro-First Rule

For every supported action, a custom macro exists to perform the core state-changing step deterministically. You MUST call the macro for that step instead of reconstructing it via generic clicks/typing on the accessibility tree, whenever a macro is available for that exact step.

Generic DOM interaction (locating elements yourself, clicking, typing) is reserved for:
- Navigation to a target (unless a dedicated navigation macro exists)
- Steps that have no corresponding macro (e.g. typing free text into a comment or message box, selecting a specific conversation)

## Macro Registry
*(Must match the host system's available custom actions)*

| Action | Macro used | What it covers | What remains generic |
| :--- | :--- | :--- | :--- |
| **Login** | `login_linkedin` | Navigating to the login page, entering email, entering password, and clicking Sign in — the full flow in one atomic call | Nothing — never split this into separate navigate/type/click steps |
| **Like Post** | `like_linkedin_post` | Locating and clicking Like on the target post, including already-liked detection | Navigating to/locating the target post first |
| **Follow / Connect** | `follow_or_connect_linkedin_profile` | Locating and clicking Follow/Connect, detecting resulting state (Following/Pending) | Navigating to the target profile or company page first |
| **Comment Post** | `comment_linkedin_post` | Opening the comment box and submitting the given comment text on the target post | Navigating to/locating the target post first |
| **Like Comment** | `like_linkedin_comment` | Locating and clicking Like on the specific target comment (not the post) | Navigating to/locating the target post and scrolling to the comment first |
| **Send Message** | `navigate_to_linkedin_messaging` (+ `send_linkedin_message` if available) | Checking the messaging inbox for an existing conversation, and sending the text once a conversation/compose box is open | See `linkedin.md`'s SEND_MESSAGE for the two-path logic: existing conversation uses the messaging inbox; a first-ever message to someone uses the "•••" (More) menu on their profile instead — never assume the inbox path applies by default |

If the host system does not expose one of the macros listed above (e.g. `follow_or_connect_linkedin_profile`, `comment_linkedin_post`, `like_linkedin_comment`, `send_linkedin_message`), fall back to generic accessibility-tree interaction for that action only, and flag in your final output that the macro was unavailable. Do not silently treat a missing macro as a reason to skip the action.

## Step Structure

Every action follows this shape, in order:
1. **Identify target** — read the target parameter(s) from the task input (profile URL, company name, post identifier, conversation contact name). If none provided and the action requires one, stop and escalate (see `system.md`, Human-in-the-Loop).
2. **Navigate** — go to the page/context where the target lives; confirm via URL/page-state per `navigation.md`.
3. **Locate** — find the specific element (post, button, conversation) belonging to that target, scrolling if necessary within the limits in `navigation.md`.
4. **Act** — call the macro (preferred) or perform the minimal generic interaction needed.
5. **Verify** — per `verification.md`, confirm the resulting state before reporting success.

## Never
- Never call a macro on a target you have not confirmed via step 1–3 above.
- Never substitute a different target (e.g. "the first post in the feed") because the intended one wasn't found — that is a **FAILURE**, not a fallback.
- Never click invisible or disabled elements.
