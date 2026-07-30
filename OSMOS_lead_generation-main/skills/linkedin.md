# LINKEDIN KNOWLEDGE

## Pages
- login
- feed
- profile (individual)
- company
- search
- messages
- post (single post / permalink view)

## Buttons
- Like
- Comment
- Follow
- Connect
- Message

## Global Rules
- **Active-state protection**: Never click a button whose text/label/aria-state implies it is already active (e.g. 'Unlike', 'Un-react', 'Following', 'Pending', aria-pressed='true'). Clicking an active-state button undoes progress. Treat that state as **SUCCESS** and stop — do not search further for a way to "confirm" it.
- **Connect** may transition to 'Pending' (request sent, not yet accepted) — this is a valid success state, distinct from 'Following'.
- **Message** requires an existing connection; if the Message button is absent or disabled on a profile, this is a **FAILURE** condition (see SEND_MESSAGE below), not something to work around.
- Never click invisible or disabled elements.
- When credentials are provided, you MUST 'Sign in' to the existing account. Never click 'Join now' or register a new account.
- You MUST use the exact credentials, search terms, and target identifiers provided in the task input. Never use placeholder values.
- All actions below require a target parameter from the task input unless explicitly marked optional. See `interaction.md` for the full step structure (identify target → navigate → locate → act → verify).

---

## SUPPORTED ACTIONS

### LOGIN
- **Goal**: Log into LinkedIn using provided credentials.
- **Target parameter**: none (uses provided email/password).
- **Preconditions**: none — the macro handles navigation itself.
- **Execution**: You MUST call the `login_linkedin` macro with the provided email and password as its sole action for this step. Do NOT reconstruct the login flow yourself via separate navigate/type/click steps — the macro performs navigation to `https://www.linkedin.com/login`, filling both fields, and clicking 'Sign in' atomically, which prevents a partial login (e.g. navigating but never submitting). Never input credentials into a "Join now", "Sign up", or registration card, and never call the macro against any page other than the login page it navigates to itself.
- **Expected Result**: The macro returns a message indicating credentials were submitted; the browser ends up on the LinkedIn feed (or a CAPTCHA/verification prompt — see Failure Conditions).
- **Failure Conditions**: If the macro's return message mentions a CAPTCHA or verification-code prompt, or credentials appear rejected — these are Tier 1 hard blockers (see `system.md`); call request_human_help immediately, do not retry.


### SEARCH_COMPANY
- **Goal**: Find a specific company page on LinkedIn.
- **Target parameter**: `company_name`
- **Preconditions**: Prefer being logged into LinkedIn first if credentials are available (results and profile details are richer), but this macro can also be used while logged out (e.g. per `system.md`'s "proceed without login" case) — do not treat "not logged in" as a reason to skip this step.
- **Execution**: You MUST use the `search_linkedin_company` macro with the provided company name. Do NOT try to use the global search bar in the UI.
- **Expected Result**: Navigated to the company search results page.
- **Failure Conditions**: Macro fails or no results found.

### LIKE_POST
- **Goal**: Like a specific post belonging to the target (a company page, a profile's activity, or a given post URL/identifier).
- **Target parameter**: `target_post` (a post URL/identifier, or a `target_profile`/`target_company` whose most recent relevant post should be liked — the task input specifies which).
- **Preconditions**: Target identified; navigated to the page containing the target post (profile activity, company page, or direct post URL) per `navigation.md`.
- **Execution**: Locate the target post (scrolling up to 3 times if needed). Call the custom `like_linkedin_post` macro on that specific post.
- **Expected Result**: Post is liked (macro returns "Success: Clicked" or "Success: Already liked").
- **Failure Conditions**: Macro returns "Failed" — scroll down once (within the 3-scroll limit) and retry per the canonical Retry Policy. If the target post cannot be located at all, this is a missing-target **FAILURE**, not a macro failure — do not like a different post instead.

### FOLLOW_CONNECT
- **Goal**: Follow or send a connection request to the target profile or company.
- **Target parameter**: `target_profile` or `target_company` (URL or name).
- **Preconditions**: Target identified; navigated to and confirmed on that specific profile/company page.
- **Execution**: Call the `follow_or_connect_linkedin_profile` macro (or, if unavailable, click the 'Follow'/'Connect' button generically per `interaction.md`'s fallback rule).
- **Expected Result**: Button state changes to 'Following' or 'Pending'.
- **Failure Conditions**: Button not found, invisible, or already in an active state on arrival (treat pre-existing 'Following'/'Pending' as **SUCCESS**, per the Active-state protection rule above — do not click again).

### COMMENT_POST
- **Goal**: Leave a specific comment (text provided in the task input) on the target post.
- **Target parameter**: `target_post` + `comment_text`.
- **Preconditions**: Target post identified and located, on the feed, company page, or post permalink view.
- **Execution**: Call the `comment_linkedin_post` macro with the target post and `comment_text` (or, if unavailable, locate the 'Comment' button on the target post, click it, type `comment_text`, click 'Post').
- **Expected Result**: The comment appears under the target post, with the exact `comment_text` provided (subject to any humanization applied upstream by the calling system).
- **Failure Conditions**: Comment box not available on the target post, or the target post cannot be located.

### LIKE_COMMENT
- **Goal**: Like a specific comment on the target post.
- **Target parameter**: `target_post` + `target_comment` (comment author name or comment identifier/snippet, to disambiguate among multiple comments).
- **Preconditions**: Target post located and comments section expanded/visible.
- **Execution**: Locate the specific comment matching `target_comment` (scrolling within comments, up to 3 times). Call the `like_linkedin_comment` macro on that comment specifically — never the post's own Like button.
- **Expected Result**: The target comment is liked.
- **Failure Conditions**: Target comment not found, or its like control not found/visible.

### SEND_MESSAGE
- **Goal**: Send a specific direct message to the target person.
- **Target parameter**: `target_conversation` (target's name) + `message_text`.
- **Preconditions**: On LinkedIn (any page).
- **Execution**: There are two distinct paths depending on whether this is the first message ever sent to this person. Determine which one applies BEFORE acting — do not default to the messaging inbox.
  1. **Check for an existing conversation first**: call the `navigate_to_linkedin_messaging` macro and look for `target_conversation` in the conversation list (scrolling up to 3 times, per `navigation.md`).
  2. **If a conversation with `target_conversation` already exists** (you have contacted them before): select it, type `message_text`, and click send (or call `send_linkedin_message` if that macro is available). This is the "already contacted" case.
  3. **If NO existing conversation is found (first message ever to this person)**: do NOT try to force it through the empty inbox. Instead, navigate to `target_conversation`'s LinkedIn profile page. Locate the "•••" (More) button that sits next to the Follow/Connect button near the top of the profile, click it to open the dropdown, and select "Message" (sometimes labelled "Send message") from that menu. This opens a message compose box directly on the profile — type `message_text` into it and send. If the "•••" menu has no Message/Send message option at all, this is a **FAILURE** (the person doesn't accept messages from non-connections) — do not substitute Connect or another action instead.
- **Expected Result**: `message_text` appears as the latest message in the conversation with `target_conversation`, via whichever path was actually used.
- **Failure Conditions**: `target_conversation`'s profile cannot be found/confirmed; the "•••" menu has no Message option and no existing conversation exists either; or the messaging/compose UI fails to load.
