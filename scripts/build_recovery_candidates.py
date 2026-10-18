#!/usr/bin/env python3
"""Build the new M5 recovery candidate pool without reading prior held-out data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ROOT = ROOT / "eval" / "recovery"
DEFAULT_CANDIDATES = RECOVERY_ROOT / "candidates.jsonl"
DEFAULT_MANIFEST = RECOVERY_ROOT / "design_manifest.json"
DEFAULT_LABEL_DIR = RECOVERY_ROOT / "label_templates"

ALLOWED_CATEGORIES = {
    "direct_request",
    "joke",
    "technical_question",
    "ongoing_discussion",
    "already_answered",
    "mention",
    "casual",
    "ambiguous",
}
DESIGN_ACTIONS = ("SILENT", "REACT", "REPLY")
LABEL_FIELDS = ("id", "history text", "message", "label", "optional note")


def h(*messages: tuple[str, str]) -> list[dict[str, str]]:
    """Create a readable history value from sender/text pairs."""
    return [{"sender": sender, "text": text} for sender, text in messages]


def cases(
    category: str,
    *items: tuple[list[dict[str, str]], str, str],
) -> dict[str, Any]:
    """Create one five-case family and validate its public category."""
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"unsupported category: {category}")
    if len(items) != 5:
        raise ValueError("every recovery family must contain exactly five cases")
    return {
        "category": category,
        "cases": [
            {"history": history, "message": {"sender": sender, "text": text}}
            for history, sender, text in items
        ],
    }


FAMILIES: list[dict[str, Any]] = [
    # SILENT coverage hypotheses. These labels never enter evaluator-facing data.
    {
        "family_id": "sf01",
        "name": "answered_technical_question",
        "design_action": "SILENT",
        **cases(
            "already_answered",
            (h(("Mina", "The cache clears automatically after ten minutes.")), "Owen", "So the cache clears after ten minutes"),
            (h(("Ravi", "Use port 5432 for the local database.")), "Noor", "Which port should I use for the local database"),
            (h(("Inez", "The staging token expires at noon UTC.")), "Kai", "Just confirming, staging token expires at noon UTC?"),
            (h(("Bea", "The export is in the shared Reports folder.")), "Luis", "Where did the export land again"),
            (h(("Tariq", "We fixed it by pinning urllib3 to 2.2.3.")), "Jo", "Was the fix the urllib3 pin"),
        ),
    },
    {
        "family_id": "sf02",
        "name": "answered_logistics_question",
        "design_action": "SILENT",
        **cases(
            "already_answered",
            (h(("Mara", "Room 204, second floor.")), "Dev", "The meetup is in room 204 right"),
            (h(("Eli", "Pickup is at 6:15 by the north entrance.")), "Sam", "What time is pickup"),
            (h(("Nia", "I moved the review to Tuesday at 11.")), "Ari", "Did the review move to Tuesday at 11?"),
            (h(("Pia", "The blue folder has the signed forms.")), "Cole", "Which folder has the signed forms"),
            (h(("Ren", "We are taking the Green Line, not the bus.")), "Zoe", "Are we taking the Green Line"),
        ),
    },
    {
        "family_id": "sf03",
        "name": "routine_progress_update",
        "design_action": "SILENT",
        **cases(
            "casual",
            (h(), "Asha", "I finished the first draft and will start edits after lunch."),
            (h(("Cal", "How is the import going?")), "June", "About halfway through; no blockers so far."),
            (h(), "Milo", "The nightly job started on schedule."),
            (h(("Eve", "Please post when the upload begins.")), "Finn", "Upload is running now."),
            (h(), "Sara", "I am heading into the client call and will send notes afterward."),
        ),
    },
    {
        "family_id": "sf04",
        "name": "work_assignment_acknowledgment",
        "design_action": "SILENT",
        **cases(
            "ongoing_discussion",
            (h(("Leah", "Can you own the release notes?")), "Mo", "Yep, I have them."),
            (h(("Drew", "Please check the mobile layout before standup.")), "Ana", "On it."),
            (h(("Hugo", "I assigned you the accessibility ticket.")), "Tess", "Got it, thanks."),
            (h(("Zara", "Could you send the agenda to the group?")), "Ben", "Will do."),
            (h(("Kim", "Take the second support shift today.")), "Pavel", "Confirmed."),
        ),
    },
    {
        "family_id": "sf05",
        "name": "settled_scheduling",
        "design_action": "SILENT",
        **cases(
            "ongoing_discussion",
            (h(("Ira", "Does 2:30 work?"), ("Mae", "Yes, sending the invite.")), "Ira", "See you then."),
            (h(("Theo", "Thursday morning is open for me."), ("Liv", "Booked for 9:00 Thursday.")), "Theo", "Perfect."),
            (h(("Uma", "Let's move the demo to Friday."), ("Vic", "Calendar updated.")), "Uma", "Thanks."),
            (h(("Nora", "I can cover the first half."), ("Gus", "I'll take the second half.")), "Nora", "That works."),
            (h(("Rae", "Meet by the lobby at 8?"), ("Sol", "8 works.")), "Rae", "Done."),
        ),
    },
    {
        "family_id": "sf06",
        "name": "reciprocal_thanks_closure",
        "design_action": "SILENT",
        **cases(
            "casual",
            (h(("Mia", "Thanks for covering my shift."), ("Jon", "Happy to help.")), "Mia", "Appreciate it."),
            (h(("Rosa", "That explanation cleared it up."), ("Em", "Glad it helped.")), "Rosa", "Thanks again."),
            (h(("Ken", "I grabbed your package."), ("Aya", "Thank you!")), "Ken", "No problem."),
            (h(("Lena", "Nice catch on that typo."), ("Bo", "Thanks.")), "Lena", "Anytime."),
            (h(("Dani", "Thanks for the quick reply."), ("Omar", "Of course.")), "Dani", "Much appreciated."),
        ),
    },
    {
        "family_id": "sf07",
        "name": "ordinary_opinion_exchange",
        "design_action": "SILENT",
        **cases(
            "ongoing_discussion",
            (h(("Jules", "I prefer the compact table."), ("Nico", "Same, it scans faster.")), "Jules", "Let's keep that one."),
            (h(("Faye", "The darker blue reads better."), ("Ash", "Agreed.")), "Faye", "Dark blue it is."),
            (h(("Remy", "Option B feels clearer."), ("Lin", "I was leaning B too.")), "Remy", "We'll use B."),
            (h(("Cara", "The short intro is enough."), ("Wes", "Yes, the long one repeats itself.")), "Cara", "Short version then."),
            (h(("Neil", "I like the first icon."), ("Yara", "Me too.")), "Neil", "First icon wins."),
        ),
    },
    {
        "family_id": "sf08",
        "name": "decision_restatement",
        "design_action": "SILENT",
        **cases(
            "ongoing_discussion",
            (h(("Al", "We'll launch the survey Monday."), ("Priya", "Monday is approved.")), "Al", "Okay, Monday launch."),
            (h(("Cleo", "Let's keep the current database."), ("Ivan", "No objections.")), "Cleo", "Current database stays."),
            (h(("Sid", "We chose the smaller venue."), ("Mona", "Confirmed with them.")), "Sid", "Smaller venue confirmed."),
            (h(("Joy", "The free tier is enough for the pilot."), ("Max", "Agreed.")), "Joy", "We'll stay on the free tier."),
            (h(("Zed", "We are dropping the extra animation."), ("Ada", "That simplifies the demo.")), "Zed", "Animation removed from scope."),
        ),
    },
    {
        "family_id": "sf09",
        "name": "availability_notice",
        "design_action": "SILENT",
        **cases(
            "casual",
            (h(), "Robin", "Offline for the next hour; text me if the build breaks."),
            (h(), "Imani", "I will be late to standup but my update is in the doc."),
            (h(), "Parker", "Working from the library this afternoon."),
            (h(), "Sana", "Stepping away for lunch, back at 1:30."),
            (h(), "Leo", "I have a dentist appointment at four and will sign back in later."),
        ),
    },
    {
        "family_id": "sf10",
        "name": "fyi_reference",
        "design_action": "SILENT",
        **cases(
            "casual",
            (h(), "Quinn", "FYI, I added the vendor notes to the shared doc."),
            (h(), "Nell", "For reference, the recording is now beside the slides."),
            (h(), "Amin", "Leaving the migration checklist here for tomorrow."),
            (h(), "Gia", "The updated brand colors are in the design folder."),
            (h(), "Toby", "I posted today's attendance numbers in the tracker."),
        ),
    },
    {
        "family_id": "sf11",
        "name": "rhetorical_comment",
        "design_action": "SILENT",
        **cases(
            "casual",
            (h(("Bev", "The printer jammed again.")), "Hal", "Why is it always the printer"),
            (h(("Niko", "The meeting moved for the third time.")), "Elle", "Can this calendar make up its mind"),
            (h(("Arun", "Another dependency update landed.")), "Meri", "What would Friday be without one more update"),
            (h(("Tia", "The coffee machine is empty.")), "Gabe", "How do we keep doing this to ourselves"),
            (h(("Luz", "The forecast changed again.")), "Dean", "Does the weather app ever know"),
        ),
    },
    {
        "family_id": "sf12",
        "name": "repeated_confirmation",
        "design_action": "SILENT",
        **cases(
            "already_answered",
            (h(("Ava", "I pushed the patch."), ("Micah", "I can see it on the branch.")), "Ava", "Great, so the patch is there."),
            (h(("Ezra", "The invoice went out."), ("Lily", "It arrived.")), "Ezra", "Good, invoice delivered."),
            (h(("Hana", "The room is reserved."), ("Pete", "The confirmation email just came.")), "Hana", "Nice, room is booked."),
            (h(("Oli", "I updated the permissions."), ("Naya", "Access works now.")), "Oli", "Perfect, permissions are fixed."),
            (h(("Vera", "The backup completed."), ("Marc", "Dashboard shows success.")), "Vera", "Okay, backup is complete."),
        ),
    },
    {
        "family_id": "sf13",
        "name": "mention_without_request",
        "design_action": "SILENT",
        **cases(
            "mention",
            (h(), "Dara", "Lurker was running during yesterday's rehearsal."),
            (h(), "Moe", "I put Lurker's metrics screenshot in the deck."),
            (h(), "Sal", "The team saw Lurker stay quiet during the demo."),
            (h(), "Kira", "We can talk about Lurker after lunch."),
            (h(), "Ivo", "Lurker is listed in the architecture diagram."),
        ),
    },
    # REACT coverage hypotheses.
    {
        "family_id": "rf01",
        "name": "release_milestone",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(("Nina", "Final checks are done.")), "Evan", "Version 1.0 is officially live!"),
            (h(), "Kofi", "We shipped the accessibility update to every user today."),
            (h(("May", "The store review cleared.")), "Zane", "Our first mobile release is out 🎉"),
            (h(), "Ruth", "The migration finished and the new system is now serving traffic."),
            (h(("Ari", "All owners signed off.")), "Lia", "The public beta has launched!"),
        ),
    },
    {
        "family_id": "rf02",
        "name": "tests_green",
        "design_action": "REACT",
        **cases(
            "technical_question",
            (h(("Cal", "The flaky suite has blocked us all week.")), "June", "All 842 tests just passed for the first time."),
            (h(), "Mira", "The end-to-end run is green across Chrome, Safari, and Firefox!"),
            (h(("Paz", "I rewrote the failing fixture.")), "Teo", "CI is finally green on the release branch."),
            (h(), "Willa", "Zero accessibility violations in the new audit."),
            (h(("Oren", "The load test is finishing now.")), "Suki", "We hit the target with no dropped requests."),
        ),
    },
    {
        "family_id": "rf03",
        "name": "meaningful_gratitude",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(), "Amal", "Thank you all for staying late to help me recover the presentation."),
            (h(), "Brynn", "I really appreciate everyone who reviewed my application this week."),
            (h(), "Cory", "Thanks for covering the launch while I was at the hospital with family."),
            (h(), "Deepa", "I could not have finished the workshop without your patient feedback."),
            (h(), "Enzo", "Huge thanks to the team for making my first week feel welcoming."),
        ),
    },
    {
        "family_id": "rf04",
        "name": "support_after_setback",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(("Fia", "How are you holding up after the interview?")), "Glen", "Didn't get it, but I'm proud I made the final round."),
            (h(), "Hadi", "The grant was declined. Taking tonight off, then I will try again."),
            (h(("Jae", "That outage was rough.")), "Kei", "Yeah, exhausted, but we learned a lot and the service is stable."),
            (h(), "Lani", "My talk did not go as planned, but I am glad I got on stage."),
            (h(("Maks", "How was the exam?")), "Nuri", "I missed the score I wanted by one point. I'll regroup."),
        ),
    },
    {
        "family_id": "rf05",
        "name": "shared_humor",
        "design_action": "REACT",
        **cases(
            "joke",
            (h(("Ola", "The deploy says it needs just five more minutes.")), "Penn", "Ah yes, computer minutes—the longest known unit of time."),
            (h(("Ria", "I named the test final_final_really_final.")), "Samir", "A strong and maintainable naming convention 😂"),
            (h(("Tess", "The robot vacuum joined the video call.")), "Uri", "Finally, someone prepared to clean up our technical debt."),
            (h(("Vale", "I fixed the bug by turning it off and on.")), "Wren", "The ancient ritual remains undefeated."),
            (h(("Xena", "The spreadsheet has 47 tabs.")), "Yuki", "At tab 48 it becomes a database, right"),
        ),
    },
    {
        "family_id": "rf06",
        "name": "incident_recovery",
        "design_action": "REACT",
        **cases(
            "technical_question",
            (h(("Zuri", "Payment processing has been down since noon.")), "Abel", "Traffic is healthy again and every queued payment cleared."),
            (h(), "Bina", "We restored the lost files from backup with no customer data missing."),
            (h(("Caz", "DNS is still unstable.")), "Dina", "Resolved—the site is reachable from all regions now."),
            (h(), "Eren", "The on-call team contained the security alert and verified no access occurred."),
            (h(("Femi", "The classroom network went offline.")), "Gita", "Everything is back before the students arrive."),
        ),
    },
    {
        "family_id": "rf07",
        "name": "welcome_and_belonging",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(("Haley", "Everyone, meet our new designer, Luca.")), "Luca", "Excited to be here and build with you all!"),
            (h(), "Mina", "Today was my first community meetup, and you made it feel easy to join."),
            (h(("Nate", "Welcome back, Pri!")), "Pri", "So happy to be back with the team."),
            (h(), "Qadir", "I just joined the study group—thanks for making room for me."),
            (h(("Rene", "Please welcome Sol to the volunteer crew.")), "Sol", "Glad to be part of this."),
        ),
    },
    {
        "family_id": "rf08",
        "name": "recognition_and_award",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(), "Tara", "Miko won the department's mentoring award today!"),
            (h(), "Uche", "Our paper received the best student project prize."),
            (h(("Vik", "The results are posted.")), "Wes", "Amina earned the scholarship!"),
            (h(), "Xim", "The organizers selected our team for the innovation showcase."),
            (h(), "Yas", "Jordan was recognized for 500 volunteer hours."),
        ),
    },
    {
        "family_id": "rf09",
        "name": "customer_praise",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(), "Zev", "A customer wrote that our accessibility fix let her complete checkout independently."),
            (h(), "Anya", "The school called our workshop the most useful session of their semester."),
            (h(("Basil", "Any feedback from the pilot?")), "Cira", "They said the dashboard saved them hours this week."),
            (h(), "Dayo", "Our first public review says support was kind and incredibly fast."),
            (h(), "Esme", "The nonprofit asked to keep using the tool after the trial."),
        ),
    },
    {
        "family_id": "rf10",
        "name": "demo_success",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(("Floyd", "How did the investor demo go?")), "Gia", "Flawless—they asked to schedule a follow-up."),
            (h(), "Hiro", "The live demo worked on the first try in front of 200 people!"),
            (h(("Isa", "Were the judges engaged?")), "Joon", "They stayed ten extra minutes to ask questions."),
            (h(), "Kemi", "Our classroom demo finished and every student completed the exercise."),
            (h(("Lars", "The rehearsal had three crashes.")), "Mara", "The final presentation ran without a single one."),
        ),
    },
    {
        "family_id": "rf11",
        "name": "learning_breakthrough",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(), "Niko", "After weeks of practice, I solved my first dynamic programming problem alone."),
            (h(), "Oma", "I gave my entire presentation in Spanish today!"),
            (h(("Pia", "The bike lessons have been tough.")), "Quin", "I rode around the block without help."),
            (h(), "Rami", "My first open-source pull request was merged."),
            (h(), "Sela", "I finally understand why the proof works, not just the steps."),
        ),
    },
    {
        "family_id": "rf12",
        "name": "community_help_impact",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(), "Tomi", "The food drive collected enough for 300 family meals."),
            (h(), "Uma", "Every student in our tutoring group passed the course."),
            (h(("Vera", "How did the cleanup go?")), "Will", "Forty volunteers cleared the whole river trail."),
            (h(), "Xavi", "We matched all twelve shelter animals with foster homes."),
            (h(), "Yara", "The fundraiser covered the community center's roof repair."),
        ),
    },
    {
        "family_id": "rf13",
        "name": "personal_good_news",
        "design_action": "REACT",
        **cases(
            "casual",
            (h(), "Zain", "I got accepted into the apprenticeship program!"),
            (h(), "Ari", "My sister is home from the hospital and doing well."),
            (h(("Bea", "Any news on the apartment?")), "Chen", "We got the keys today!"),
            (h(), "Dora", "I paid off my last student loan this morning."),
            (h(), "Eli", "We adopted the puppy we have been fostering."),
        ),
    },
    # REPLY coverage hypotheses.
    {
        "family_id": "pf01",
        "name": "direct_named_request",
        "design_action": "REPLY",
        **cases(
            "direct_request",
            (h(), "Fara", "Lurker, summarize the three decisions in this thread."),
            (h(("Gus", "The deployment logs are above.")), "Hana", "Lurker please identify the first error."),
            (h(), "Ivan", "Hey Lurker, can you draft a polite reminder for the volunteers"),
            (h(("Jia", "We have two venue options.")), "Kurt", "Lurker, compare them for accessibility."),
            (h(), "Lina", "Lurker tell me what information is missing from this bug report"),
        ),
    },
    {
        "family_id": "pf02",
        "name": "unanswered_technical_question",
        "design_action": "REPLY",
        **cases(
            "technical_question",
            (h(), "Moe", "Why does the API return 429 only during the batch job?"),
            (h(("Nia", "The container starts locally.")), "Oli", "What could make it exit immediately in CI"),
            (h(), "Paz", "Is it safe to rotate this signing key while sessions are active"),
            (h(("Rae", "The query is fast with ten rows.")), "Sol", "How should we index it for millions of records?"),
            (h(), "Tia", "What is the difference between a retry and a circuit breaker"),
        ),
    },
    {
        "family_id": "pf03",
        "name": "indirect_help_request",
        "design_action": "REPLY",
        **cases(
            "direct_request",
            (h(), "Uma", "I'm stuck turning these interview notes into a short summary."),
            (h(), "Vic", "I cannot figure out how to make this form keyboard accessible."),
            (h(("Wen", "The deadline is tomorrow.")), "Xia", "I could use a second set of eyes on this outline."),
            (h(), "Yuri", "Not sure how to explain this error to a nontechnical client."),
            (h(), "Zoe", "I need a way to compare these two CSV files without checking every row."),
        ),
    },
    {
        "family_id": "pf04",
        "name": "request_for_judgment",
        "design_action": "REPLY",
        **cases(
            "direct_request",
            (h(("Abe", "Option A is faster; B is easier to maintain.")), "Bri", "Which would you choose for a three-week prototype?"),
            (h(), "Cem", "Does this apology sound sincere or defensive"),
            (h(("Dia", "We can add one more feature before demo day.")), "Evan", "Should we prioritize search or exports?"),
            (h(), "Faye", "Is this graph clear enough for a general audience"),
            (h(("Gio", "The room costs more but has step-free access.")), "Hope", "Is the extra cost worth it for the event?"),
        ),
    },
    {
        "family_id": "pf05",
        "name": "troubleshooting_needs_details",
        "design_action": "REPLY",
        **cases(
            "technical_question",
            (h(), "Inez", "The script keeps failing. What should I check first?"),
            (h(("Jay", "Login works for me.")), "Kira", "It fails for one user—how do I narrow that down"),
            (h(), "Lyle", "The page is blank after deploy, but there is no screenshot yet. Any ideas?"),
            (h(), "Mina", "My tests pass alone and fail together. Where should I look"),
            (h(("Noah", "The sensor stopped reporting overnight.")), "Ola", "What details do we need before replacing it?"),
        ),
    },
    {
        "family_id": "pf06",
        "name": "safety_and_security_question",
        "design_action": "REPLY",
        **cases(
            "technical_question",
            (h(), "Pru", "Can I paste an access token into the public issue if I revoke it later"),
            (h(), "Qasim", "Is it okay to email this spreadsheet if it contains student phone numbers?"),
            (h(("Rina", "This link asks me to sign in again.")), "Sven", "How can I tell whether it is phishing"),
            (h(), "Tala", "Should we allow the app to log full payment requests during debugging"),
            (h(), "Umar", "Is a 401 response safe to ignore during account creation"),
        ),
    },
    {
        "family_id": "pf07",
        "name": "summary_or_transformation_request",
        "design_action": "REPLY",
        **cases(
            "direct_request",
            (h(("Vera", "We chose Friday."), ("Walt", "Mina owns the slides."), ("Xiu", "Budget stays at $200.")), "Yen", "Can someone turn those decisions into a checklist"),
            (h(("Zara", "The pilot had 40 users."), ("Adam", "Six reported login trouble.")), "Belle", "Summarize that in one sentence for the update."),
            (h(("Cory", "First call the venue."), ("Dina", "Then confirm the speakers.")), "Eli", "Could you format this as numbered steps?"),
            (h(("Femi", "Users want filters."), ("Gia", "They also asked for CSV export.")), "Hugo", "Please group the feedback by theme"),
            (h(("Iris", "Monday: research."), ("Jon", "Tuesday: prototype.")), "Kaya", "Make a short schedule from this"),
        ),
    },
    {
        "family_id": "pf08",
        "name": "planning_advice",
        "design_action": "REPLY",
        **cases(
            "direct_request",
            (h(), "Luz", "How should we divide a two-hour hackathon rehearsal?"),
            (h(), "Marek", "What should I prepare before interviewing three users tomorrow"),
            (h(("Nell", "We have four volunteers and 60 guests.")), "Omar", "Can you suggest a simple check-in plan?"),
            (h(), "Pia", "What is a realistic order for migrating these five small services"),
            (h(("Quin", "The workshop is 45 minutes.")), "Rosa", "How much time should we leave for questions?"),
        ),
    },
    {
        "family_id": "pf09",
        "name": "ambiguous_request_needs_clarification",
        "design_action": "REPLY",
        **cases(
            "ambiguous",
            (h(), "Seth", "Can you fix the report for me"),
            (h(("Tara", "I uploaded two versions.")), "Uma", "Use the better one."),
            (h(), "Vic", "Make the homepage feel more modern"),
            (h(("Wes", "The numbers do not match.")), "Xena", "Can you check it?"),
            (h(), "Yara", "Help me get ready for tomorrow"),
        ),
    },
    {
        "family_id": "pf10",
        "name": "unanswered_followup",
        "design_action": "REPLY",
        **cases(
            "ongoing_discussion",
            (h(("Zed", "The import failed at row 80."), ("Ava", "I can inspect it after lunch.")), "Zed", "Could a duplicate ID cause that error?"),
            (h(("Bo", "The vendor supports SSO.")), "Cami", "Do they also support automatic user removal"),
            (h(("Dev", "We can host the event in June.")), "Esra", "Which weekend has the fewest conflicts?"),
            (h(("Finn", "The new plan is cheaper.")), "Gwen", "What limits would we lose by switching?"),
            (h(("Hari", "The backup restored successfully.")), "Ivy", "How do we verify no records are missing"),
        ),
    },
    {
        "family_id": "pf11",
        "name": "explain_a_concept",
        "design_action": "REPLY",
        **cases(
            "technical_question",
            (h(), "Jamal", "Explain rate limiting like I am new to APIs."),
            (h(), "Kira", "What does statistical significance mean in plain language"),
            (h(), "Liam", "Why does keyboard focus order matter for accessibility?"),
            (h(), "Mona", "Can you explain the difference between encryption and hashing"),
            (h(), "Ned", "What is a container image and how is it different from a running container"),
        ),
    },
    {
        "family_id": "pf12",
        "name": "review_request",
        "design_action": "REPLY",
        **cases(
            "direct_request",
            (h(), "Ona", "Please review this error message: 'Something went wrong.' What should it say instead?"),
            (h(), "Pavel", "Can you check whether this survey question is leading: 'How helpful was our great workshop?'"),
            (h(), "Quincy", "Review this subject line for clarity: 'Important update.'"),
            (h(("Rhea", "The function is pasted above.")), "Sami", "Can you spot any edge cases I missed"),
            (h(), "Tori", "Does this agenda leave enough time for discussion: 40 minutes of slides, 5 minutes of questions"),
        ),
    },
    {
        "family_id": "pf13",
        "name": "semantic_question_without_punctuation",
        "design_action": "REPLY",
        **cases(
            "technical_question",
            (h(), "Uma", "how do I reset the local database"),
            (h(), "Vik", "is this license okay for a commercial project"),
            (h(("Wen", "The build takes 18 minutes.")), "Xia", "what is making it so slow"),
            (h(), "Yosef", "could someone explain why this request gets a 403"),
            (h(), "Zola", "which file should contain the environment variables"),
        ),
    },
]


def normalized_text(row: dict[str, Any]) -> str:
    """Return a conservative normalized string for duplicate checks."""
    parts = [item["text"] for item in row["history"]] + [row["message"]["text"]]
    return re.sub(r"[^a-z0-9]+", " ", " ".join(parts).lower()).strip()


def build_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build public candidates and a physically separate owner-only design manifest."""
    rows: list[dict[str, Any]] = []
    family_manifest: list[dict[str, Any]] = []
    next_id = 1
    for family in FAMILIES:
        ids: list[str] = []
        for case in family["cases"]:
            scenario_id = f"rc{next_id:03d}"
            next_id += 1
            ids.append(scenario_id)
            rows.append(
                {
                    "id": scenario_id,
                    "family_id": family["family_id"],
                    "category": family["category"],
                    "history": case["history"],
                    "message": case["message"],
                }
            )
        family_manifest.append(
            {
                "family_id": family["family_id"],
                "name": family["name"],
                "design_action": family["design_action"],
                "candidate_ids": ids,
            }
        )

    validate_rows(rows, family_manifest)
    manifest = {
        "artifact_version": "lurker-m5-recovery-design-v1",
        "warning": (
            "Owner-only authoring metadata. design_action is a coverage hypothesis, "
            "not a human label or evaluation target. Do not share with evaluators."
        ),
        "candidate_count": len(rows),
        "family_count": len(family_manifest),
        "family_size": 5,
        "design_action_counts": dict(
            Counter(family["design_action"] for family in FAMILIES for _ in family["cases"])
        ),
        "families": family_manifest,
    }
    return rows, manifest


def validate_rows(rows: list[dict[str, Any]], families: list[dict[str, Any]]) -> None:
    """Validate size, uniqueness, family structure, and blind public fields."""
    if len(rows) != 195:
        raise ValueError(f"expected 195 candidates, found {len(rows)}")
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("candidate ids must be unique")
    if any(not scenario_id.startswith("rc") for scenario_id in ids):
        raise ValueError("recovery ids must use the rc prefix")
    family_ids = [family["family_id"] for family in families]
    if len(family_ids) != 39 or len(set(family_ids)) != 39:
        raise ValueError("expected 39 unique families")
    counts = Counter(row["family_id"] for row in rows)
    if set(counts.values()) != {5}:
        raise ValueError("every family must contain exactly five candidates")
    if any(row["category"] not in ALLOWED_CATEGORIES for row in rows):
        raise ValueError("candidate contains unsupported category")
    if any(len(row["history"]) > 5 for row in rows):
        raise ValueError("history may contain at most five messages")
    if len({normalized_text(row) for row in rows}) != len(rows):
        raise ValueError("candidate pool contains exact normalized duplicates")
    forbidden = {"label", "labels", "consensus", "prediction", "design_action", "split"}
    if any(forbidden & set(row) for row in rows):
        raise ValueError("candidate rows expose evaluator-hidden fields")


def format_history(history: list[dict[str, str]]) -> str:
    """Render history for a non-programmer-friendly CSV cell."""
    if not history:
        return "No earlier messages"
    return "\n".join(f"{item['sender']}: {item['text']}" for item in history)


def evaluator_order(rows: list[dict[str, Any]], evaluator: str) -> list[dict[str, Any]]:
    """Return a deterministic, evaluator-specific random order."""
    seed = int.from_bytes(hashlib.sha256(f"recovery-v1:{evaluator}".encode()).digest()[:8])
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def write_outputs(
    candidates_path: Path,
    manifest_path: Path,
    label_dir: Path,
) -> list[Path]:
    """Write candidates, owner-only design metadata, and three blank label files."""
    protected_root = (ROOT / "results" / "m5_heldout").resolve()
    for path in (candidates_path, manifest_path, label_dir):
        resolved = path.resolve()
        if resolved == protected_root or protected_root in resolved.parents:
            raise ValueError("recovery generation may not write inside original M5 evidence")

    rows, manifest = build_rows()
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest["candidate_sha256"] = hashlib.sha256(candidates_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    outputs: list[Path] = []
    for evaluator in ("a1", "a2", "a3"):
        output = label_dir / f"recovery_labels_{evaluator}.csv"
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            for row in evaluator_order(rows, evaluator):
                writer.writerow(
                    {
                        "id": row["id"],
                        "history text": format_history(row["history"]),
                        "message": f"{row['message']['sender']}: {row['message']['text']}",
                        "label": "",
                        "optional note": "",
                    }
                )
        outputs.append(output)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--label-dir", type=Path, default=DEFAULT_LABEL_DIR)
    args = parser.parse_args()
    outputs = write_outputs(args.candidates, args.manifest, args.label_dir)
    print(f"candidates={args.candidates} rows=195 families=39")
    print(f"owner_manifest={args.manifest} design_balance=65/65/65")
    for output in outputs:
        print(f"blank_label_file={output}")
    print("human_labels_created=0 model_calls=0 aws_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
