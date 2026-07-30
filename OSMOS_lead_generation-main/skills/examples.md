EXECUTION EXAMPLES

Example 1: Login

Call login_linkedin with the provided email and password.
Macro returns "Login credentials submitted. If you see a CAPTCHA, call request_human_help."
Verify URL is /feed.
Result: SUCCESS — logged in.

Example 2: Like Post (targeted)
Task input: target_company = "Acme Corp".

Navigate to the Acme Corp company page.
Verify URL/page matches "Acme Corp".
Locate the company's most recent post (scroll if not immediately visible, max 3 times).
Call like_linkedin_post on that specific post.
Result: "Success: Clicked" -> Report SUCCESS with target = Acme Corp's latest post.

Example 3: Like Post — already liked

Navigate to target post.
Call like_linkedin_post.
Macro returns "Success: Already liked".
Result: SUCCESS — no further action needed, do not click again.

Example 4: Follow/Connect (targeted)
Task input: target_profile = "linkedin.com/in/jane-doe", action = Connect.

Navigate to linkedin.com/in/jane-doe.
Verify the profile name matches "Jane Doe".
Check the connect button's current label first — if it already reads 'Pending', report SUCCESS immediately without clicking (Active-state protection).
Otherwise, call follow_or_connect_linkedin_profile.
Verify the button now reads 'Pending'.
Result: SUCCESS.

Example 5: Comment Post (targeted)
Task input: target_post = <post_id_123>, comment_text = "Great insights on Q3 cloud migration."

Navigate to the page containing <post_id_123> (feed or permalink).
Locate the specific post by its identifier (scroll up to 3 times if needed).
Call comment_linkedin_post with the target post and the provided comment_text.
Verify the comment now appears under the post with matching text.
Result: SUCCESS.

Example 6: Like Comment (targeted, disambiguated)
Task input: target_post = <post_id_123>, target_comment = "comment by John Smith mentioning 'infrastructure budget'".

Navigate to <post_id_123> and expand the comments section.
Scroll through comments (max 3 times) looking for the one from "John Smith" mentioning "infrastructure budget".
Once located, call like_linkedin_comment on that specific comment — not the post's own Like button.
Verify only that comment shows a liked state.
Result: SUCCESS.

Example 7a: Send Message — already contacted before
Task input: target_conversation = "Jane Doe", message_text = "Hi Jane, following up on our earlier chat about your Q3 roadmap."

Call navigate_to_linkedin_messaging.
Locate the existing conversation with "Jane Doe" (scroll conversation list up to 3 times if needed) — found.
Select it, type message_text, click send (or call send_linkedin_message with message_text if available).
Verify the message appears as the latest entry in the conversation with "Jane Doe".
Result: SUCCESS.

Example 7b: Send Message — first message ever (no existing conversation)
Task input: target_conversation = "John Smith", message_text = "Hi John, loved your recent post on cloud migration strategy."

Call navigate_to_linkedin_messaging.
Scroll the conversation list up to 3 times — "John Smith" is not present (no prior conversation).
Do NOT try to force a send through the inbox. Navigate instead to John Smith's LinkedIn profile.
Locate the "•••" (More) button next to the Follow/Connect button and click it.
Select "Message" (or "Send message") from the dropdown — a compose box opens on the profile.
Type message_text into the compose box and send.
Verify the message appears as the latest entry in the now-created conversation with "John Smith".
Result: SUCCESS.

Example 8: Failure and escalation (element not found)
Task input: target_post = <post_id_999> (does not exist on the visible page).

Navigate to the expected page.
Scroll 3 times searching for <post_id_999>.
Not found after 3 scrolls — first attempt exhausted.
Retry once: reload the section, scroll up to 3 times again.
Still not found — retry policy exhausted (2 attempts total).
Result: FAILURE — call request_human_help reporting "target post <post_id_999> not found after 2 attempts", per Tier 2 escalation. Do not substitute a different post.

Example 9: Hard blocker (CAPTCHA during login)

Call login_linkedin with the provided credentials.
A CAPTCHA challenge appears after submission.
Result: Immediately call request_human_help (Tier 1 — no retry attempted) and wait for the user's response before proceeding.

Example 10: Recovering credentials via request_human_help

Task input does not include LinkedIn email/password, but the task requires being logged in.
Call request_human_help with question: "Please provide LinkedIn login email and password to proceed."
Tool result: "User replied: email: jane@example.com, password: hunter2".
Do NOT call request_human_help again. Do NOT report failure.
Very next action: call login_linkedin with email="jane@example.com", password="hunter2" (extracted from the reply).
Result: SUCCESS — logged in, proceed with the rest of the task.
