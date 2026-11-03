# Reddit pilot report (2021 to 2023)

For the site owner. This covers the pilot run on the Reddit dump for 1 January 2021 to 31 December 2023 (the dump ends in 2023). Nothing from `site/` is committed; the rebuilt site is in the working tree for you to preview.

## Summary

- 269,988 candidate comments from 27 subreddits became **6,423 recommendations** that passed the AI review, which became **383 listed Reddit courses** (each has at least 2 different recommenders). 253 of them exist only on Reddit and got their own course page.
- The whole pilot cost **about $2.26** in AI calls. Full history is projected at roughly **$8 (range $6 to $11)**.
- The Hacker News list did not change: the 1,376 courses have identical ids, ranks and scores to the committed site.
- Spam detection looks good (10 of 10 spot-checked spam flags were right). The weak spot is the opposite one: about 1 in 5 kept comments is not really a recommendation.
- The "rising" badge is meaningless on a 3-year window (217 of 383 courses have it). Fine for the pilot, needs the thresholds below for full history.
- r/learnprogramming alone produces 59% of the recommendations. Most business and marketing subreddits produce very little.

## How the funnel worked

1. Rules keep comments that name a course, provider or course link: 269,988 down to **9,660** (the "pool").
2. A model (Haiku) reads each pool comment and decides if it recommends a specific course and whether it is spam: 6,423 kept, 3,082 "not a recommendation", 155 spam after a second opinion.
3. 310 spam-flagged comments were re-read by a stronger model (Sonnet); it cleared 155 of them.
4. Rules also dropped, before the model: 8,271 for spam wording, 299 repeat promoters, 51 duplicates, plus comments that were too long or negative.

## Per subreddit

"Candidates" are comments that reached us from the dump. "Rule-kept" are those that entered the review pool. "Model-kept" are confirmed course recommendations. "Model spam" are comments the model flagged as promotion after the second opinion. The remaining pool comments were "not a recommendation".

| Subreddit | Candidates | Rule-kept | Model-kept | Model spam | Kept / pool |
|---|---:|---:|---:|---:|---:|
| learnprogramming | 75,996 | 5,413 | 3,802 | 31 | 70% |
| webdev | 20,467 | 1,004 | 656 | 10 | 65% |
| learnmachinelearning | 8,133 | 846 | 663 | 9 | 78% |
| Entrepreneur | 26,543 | 371 | 141 | 24 | 38% |
| Python | 10,095 | 367 | 237 | 8 | 65% |
| marketing | 9,573 | 361 | 201 | 9 | 56% |
| MachineLearning | 6,441 | 211 | 151 | 5 | 72% |
| ExperiencedDevs | 10,852 | 162 | 71 | 2 | 44% |
| SEO | 5,331 | 143 | 73 | 8 | 51% |
| PPC | 3,800 | 104 | 63 | 3 | 61% |
| smallbusiness | 11,961 | 98 | 48 | 8 | 49% |
| programming | 22,849 | 93 | 50 | 4 | 54% |
| productivity | 5,086 | 90 | 48 | 2 | 53% |
| getdisciplined | 5,663 | 70 | 34 | 0 | 49% |
| startups | 5,603 | 62 | 46 | 0 | 74% |
| ChatGPT | 19,226 | 60 | 38 | 4 | 63% |
| artificial | 2,004 | 38 | 27 | 3 | 71% |
| EntrepreneurRideAlong | 2,776 | 33 | 13 | 0 | 39% |
| Emailmarketing | 866 | 30 | 7 | 16 | 23% |
| SaaS | 2,085 | 29 | 17 | 5 | 59% |
| selfhosted | 5,879 | 20 | 5 | 1 | 25% |
| Notion | 2,489 | 15 | 11 | 2 | 73% |
| LocalLLaMA | 2,065 | 13 | 11 | 0 | 85% |
| ObsidianMD | 2,661 | 10 | 4 | 0 | 40% |
| socialmedia | 544 | 8 | 3 | 0 | 38% |
| bigseo | 540 | 7 | 3 | 1 | 43% |
| bujo | 460 | 2 | 0 | 0 | 0% |
| indiehackers, PKMS, ClaudeAI | 0 | 0 | 0 | 0 | none in the 2021 to 2023 data |

**r/LocalLLaMA:** the earlier "kept 0" in a fetch log was a counting artefact. It has 2,065 candidates, 13 in the pool and 11 kept, so it works; it is just a small yield.

## Top 50 Reddit courses

Ranked on Reddit data only, never mixed with Hacker News. "Recommenders" counts different people who recommend it.

| Rank | Course | Provider | Recommenders | Score | Badges |
|---:|---|---|---:|---:|---|
| 1 | CS50: Introduction to Computer Science | Harvard University | 931 | 746.6 | rising |
| 2 | Machine Learning (Andrew Ng) | Coursera | 286 | 239.8 | rising |
| 3 | The Web Developer Bootcamp | Udemy | 215 | 187.4 | rising |
| 4 | Practical Deep Learning for Coders | fast.ai | 118 | 101.9 | rising |
| 5 | 100 Days of Code: The Complete Python Pro Bootcamp | Udemy | 106 | 93.5 | rising |
| 6 | Learning How to Learn: Powerful mental tools to help you master tough subjects | Coursera | 97 | 87.3 | rising |
| 7 | Deep Learning Specialization (Andrew Ng) | Coursera | 89 | 79.6 | rising |
| 8 | The Complete JavaScript Course: Build a Real-World Project | Udemy | 89 | 78.2 | rising |
| 9 | The Complete Web Development Bootcamp (Angela Yu) | Udemy | 83 | 74.1 | rising |
| 10 | Responsive Web Design | freeCodeCamp | 80 | 72.2 | rising |
| 11 | Full Stack Open | University of Helsinki | 75 | 70.4 | rising |
| 12 | CS50's Web Programming with Python and JavaScript | edX | 56 | 53.8 | rising |
| 13 | The Elements of Computing Systems (Nand2Tetris) | nand2tetris.org | 56 | 52.0 | rising |
| 14 | Java Programming MOOC | University of Helsinki | 48 | 45.7 | rising |
| 15 | Automate the Boring Stuff with Python | Udemy | 46 | 40.0 | rising |
| 16 | Algorithms, Part I | Coursera | 43 | 39.9 | rising |
| 17 | 6.006 Introduction to Algorithms | MIT OpenCourseWare | 42 | 39.1 | rising |
| 18 | The Odin Project Foundations Course | The Odin Project | 41 | 38.5 | rising |
| 19 | The Odin Project Full Stack JavaScript Curriculum | The Odin Project | 42 | 37.4 | rising |
| 20 | Machine Learning Specialization (University of Washington, Carlos Guestrin and Emily Fox) | Coursera | 38 | 36.3 | rising |
| 21 | JavaScript Algorithms and Data Structures | freeCodeCamp | 37 | 35.1 | rising |
| 22 | 18.06 Linear Algebra (Gilbert Strang) | MIT OpenCourseWare | 36 | 34.8 | rising |
| 23 | CS229 Machine Learning | Stanford University | 36 | 34.0 | rising |
| 24 | Introduction to Computer Science and Programming in Python | MIT OpenCourseWare | 38 | 33.5 | rising |
| 25 | CS50P: Introduction to Programming with Python | Harvard University | 42 | 33.3 | rising |
| 26 | CS50's Introduction to Programming with Python | Harvard University (CS50) | 38 | 31.3 | rising |
| 27 | Complete Python Bootcamp: Go from Zero to Hero in Python 3 | Udemy | 31 | 30.4 | rising |
| 28 | An Introduction to Interactive Programming in Python | Coursera | 36 | 30.1 | rising |
| 29 | CS61A: Structure and Interpretation of Computer Programs | UC Berkeley | 27 | 26.7 | rising |
| 30 | React - The Complete Guide (incl React Router & Redux) | Udemy | 25 | 26.7 | rising |
| 31 | 6.0001 Introduction to Computer Science and Programming in Python | MIT OCW | 28 | 25.9 | rising |
| 32 | Learn Python | Codecademy | 22 | 20.8 | rising |
| 33 | CS61B Data Structures | UC Berkeley | 20 | 20.7 | rising |
| 34 | Python Programming MOOC | University of Helsinki | 18 | 17.6 | rising |
| 35 | Java Masterclass | Udemy | 16 | 15.7 | rising |
| 36 | Algorithms, Part II | Coursera | 14 | 15.6 | rising |
| 37 | CS231n: Convolutional Neural Networks for Visual Recognition | Stanford University | 15 | 15.3 | rising |
| 38 | The Missing Semester of Your CS Education | MIT CSAIL | 14 | 14.9 | rising |
| 39 | The Odin Project JavaScript Path | The Odin Project | 14 | 14.6 | rising |
| 40 | CS50's Introduction to Artificial Intelligence with Python | Harvard University | 12 | 14.6 | rising |
| 41 | Python for Data Science and Machine Learning | Udemy | 12 | 12.7 | rising |
| 42 | Python for Everybody | Coursera | 12 | 12.5 | rising |
| 43 | Digital Marketing | HubSpot Academy | 13 | 12.4 | rising |
| 44 | Google Ads Certification | Google | 13 | 12.3 | rising |
| 45 | Advanced CSS and Sass | Udemy | 11 | 12.2 | rising |
| 46 | JavaScript and jQuery | Codecademy | 13 | 12.0 | rising |
| 47 | CS224N: Natural Language Processing with Deep Learning | Stanford University | 11 | 11.5 | rising |
| 48 | Python Course | freeCodeCamp | 13 | 11.4 | rising |
| 49 | The Modern JavaScript Bootcamp | Udemy | 11 | 10.5 | rising |
| 50 | Inbound Marketing | HubSpot Academy | 10 | 10.5 | rising |

Things to know about this list:
- **Duplicates survive.** Several entries are the same course under two names: CS50P and "CS50's Introduction to Programming with Python" (ranks 25 and 26), and "Introduction to Computer Science and Programming in Python" and "6.0001" from MIT (24 and 31). A tighter merge pass would lift the real totals and tidy the list. It does not affect the HN side.
- The list is dominated by free, general programming courses. Paid Udemy bestsellers rank high, which is the intended behaviour for third-party recommendations.
- Business and marketing courses barely appear: only HubSpot Academy (ranks 43 and 50) and Google Ads Certification (44) reach the top 50.

## Spot checks by hand

**20 random model-kept comments: 16 looked right, 4 did not.**
- Wrong: a Tom Scott timezone video (a talk, not a course); a question asking "do you think CS50 and OSSU would be good?" (the asker, not a recommender); a generic "do a supplemental Udemy course for $15" labelled as a React course; a comment about getting a degree that never recommends MIT OpenCourseWare.
- One of the 16 was borderline (a FrontEnd Masters mention inside a long answer).
- So the model still lets through questions and generic advice. The two-recommender minimum and one-vote-per-person scoring soften this, but the review prompt could be tightened (see below).

**10 random spam-flagged comments: 10 of 10 were right.** They were a Codecademy referral link, a homelab answer ending in a YouTube plug, a "check out Pioneer Academy's course" ad, an email-software affiliate link, an AI-written list with an affiliate link, a Go tutorial site written by the poster, a tutoring offer, a review-blog reprint, a data-science answer that ends by promoting the poster's own blog, and a Udemy recommendation that ends "via the link I shared" (an affiliate pattern). Because spam detection is working, `REDDIT_SPAM` was not changed.

## Cost

| Step | Actual cost |
|---|---:|
| 300-comment sample review (Haiku) | $0.027 |
| Review of the rest of the pool, 9,360 comments (Haiku) | $0.920 |
| Spam recheck, 310 comments (Sonnet) | $0.522 |
| Merging course names (canonicalize), 3,667 names | $0.412 |
| Reddit-only dedupe, 146 merges | $0.176 |
| Summaries, 478 courses | $0.199 |
| Images | no AI cost (link previews and YouTube thumbnails) |
| **Total** | **about $2.26** |

The sample cost $0.00009 per comment. The gate was $10, so no stop was needed.

## Projection for full history

Assumptions: the dump has 2005 to 2023, and the API adds 2024 to early 2026 later. Reddit was smaller before 2021, so the earlier 16 years are counted as roughly 5.6 years' worth of the 2021 to 2023 volume, and 2024 to 2026 as about 0.8 of the pilot. That gives about **3.7 times the pilot**. These are estimates, not measurements.

| | Pilot | Full history (estimate) |
|---|---:|---:|
| Listed Reddit courses (2+ recommenders) | 383 | 800 to 1,300 |
| Reddit-only course pages | 253 | 550 to 900 |
| Site files (HN + Reddit) | 1,706 | 2,500 to 3,200 |
| AI cost | $2.26 | $6 to $11, central $8 |

Courses grow more slowly than comments (the same popular courses keep recurring), so the file count stays far below the 19,000-file build limit. Cost is not the constraint either.

## Subreddits proposed for dropping

Dropping would not change the HN list. Reasons are yield and quality, not policy.

| Subreddit | Why |
|---|---|
| bujo | 460 candidates, 2 in the pool, 0 kept |
| socialmedia | 3 kept from 544 |
| bigseo | 3 kept from 540 |
| ObsidianMD | 4 kept from 2,661 (note-taking tools, not courses) |
| selfhosted | 5 kept from 5,879 (mostly tools and videos) |
| Emailmarketing | 7 kept but 16 spam, the worst quality of any subreddit (23% kept) |
| indiehackers, PKMS, ClaudeAI | no data in the 2021 to 2023 dump. Keep ClaudeAI for the 2024+ API run; indiehackers and PKMS can go unless the older dump has them. |

Borderline, keep for now: EntrepreneurRideAlong (13 kept), Notion (11), LocalLLaMA (11), SaaS (17). They are small but cost almost nothing. The larger business subreddits (Entrepreneur, smallbusiness, startups, ExperiencedDevs) have a poor yield but still add a few non-programming courses, so keep them.

## Proposed Reddit badge thresholds

No badge code was changed in this task. On a 3-year window every course has 100% of its votes in the last 3 years, so "rising" everywhere, and no "classic" or "evergreen" (which need an 8-year span), are artefacts of the window, not bad rules. 217 of 383 courses are "rising" and 9 are "hidden gems".

Proposed once full history is in, replacing `BADGE_RULES["reddit"]`:

| Rule | HN now | Proposed for Reddit | Why |
|---|---|---|---|
| rising_min (recommenders) | 3 | 5 | Reddit has many more voices; 3 is too easy |
| rising_share (share of votes in last 3 years) | 0.6 | 0.7 | Reddit volume is skewed to recent years anyway |
| classic_span / evergreen_span | 8 | 8 | keep |
| evergreen_years | 6 | 6 | keep |
| hidden gem (2 to 4 recommenders) strong share | 0.75 | 0.8 | upvotes already reward quality, so require stronger agreement |

I would apply these after the full history run so the badge counts can be checked against real data.

## Other proposals and concerns

1. **Tighten the Reddit review prompt** to reject questions asked by the person seeking advice, generic advice with no named course, and single videos or talks. The whole review costs about $1 per pilot, so a re-run is cheap.
2. **Run a second merge pass** for duplicate course names (see the top 50 notes).
3. Decisions needed from you: which subreddits to drop, and whether to run full history (dump 2005 to 2020, plus the 2024 to 2026 API).

## Full history (2005 to 2023, local dump)

Run on the full local dump (no API; 2024 onwards still held). Fetch took 59m39s; 752,450 candidate comments (270k in the pilot).

- **Funnel:** 27,154 pool comments reviewed (9,660 pilot + 17,494 new); 18,222 kept as recommendations, 8,401 "not a recommendation", 435 spam after the Sonnet recheck (631 flagged, 333 cleared).
- **Listed Reddit courses (2+ recommenders): 934** (pilot 383; projection was 800 to 1,300). 674 exist only on Reddit and have their own page. The union site has 2,050 courses and 2,127 files (limit 19,000).
- **Spend: about $8.70** in AI calls (pilot projection $8, range $6 to $11); gate was $15. Sample $0.029, review $1.644, spam recheck $0.921, canonicalize $4.895 (6,061 names; about 12x the pilot per name because the catalog is larger), dedupe $0.372 + $0.357 (second pass), summaries $0.433 + $0.048.
- **Badges** with the proposed thresholds applied (rising_min 5, rising_share 0.7, gem_strong 0.8), counted on the first build (939 courses): before (HN rules) classic 21, evergreen 79, rising 121, hidden gem 11; after: classic 21, evergreen 79, rising 54, hidden gem 10. Final build (934 courses) after the second dedupe: classic 21, evergreen 81, rising 50, hidden gem 10.
- **HN:** id, rank and score identical for all 1,376 courses. 41 HN courses lost their image (see concerns in the task report): the image step drops pictures shared by 3 or more courses, and Reddit-only courses now share some.
- **Remaining duplicates:** the MIT 6.0001 family still appears several times: "Introduction to Computer Science and Programming in Python" (rank 5), "6.0001 ..." (22), "6.00 ... MITx" (41) and "6.001x ... edX" (48). The Odin Project Foundations and Full Stack are kept apart (distinct tracks). The CS50P duplicate and the 6.0001/edX pair from the pilot are gone from the top 50 apart from the MIT family above. A second dedupe pass merged 127 more entries.

### Top 25 Reddit courses

| Rank | Course | Provider | Recommenders | Score | Badges |
|---:|---|---|---:|---:|---|
| 1 | CS50: Introduction to Computer Science | Harvard University | 2011 | 2981.7 | classic, evergreen |
| 2 | Machine Learning (Andrew Ng) | Coursera | 1179 | 1810.7 | classic, evergreen |
| 3 | The Web Developer Bootcamp | Udemy | 553 | 616.6 | - |
| 4 | Practical Deep Learning for Coders | fast.ai | 324 | 434.4 | classic, evergreen |
| 5 | Introduction to Computer Science and Programming in Python | MIT OpenCourseWare | 263 | 411.4 | classic, evergreen |
| 6 | Learning How to Learn: Powerful mental tools to help you master tough subjects | Coursera | 241 | 323.1 | classic, evergreen |
| 7 | Deep Learning Specialization (Andrew Ng) | Coursera | 253 | 279.8 | - |
| 8 | Algorithms, Part I | Coursera | 182 | 261.8 | classic, evergreen |
| 9 | 6.006 Introduction to Algorithms | MIT OpenCourseWare | 131 | 217.1 | classic, evergreen |
| 10 | The Elements of Computing Systems (Nand2Tetris) | nand2tetris.org | 154 | 211.4 | classic, evergreen |
| 11 | CS101 Introduction to Computer Science | Coursera | 153 | 210.5 | classic, evergreen |
| 12 | CS229 Machine Learning | Stanford University | 127 | 209.5 | classic, evergreen |
| 13 | Learn Python | Codecademy | 132 | 184.2 | classic, evergreen |
| 14 | The Complete Web Developer Course (Angela Yu) | Udemy | 146 | 180.0 | classic, evergreen |
| 15 | Responsive Web Design | freeCodeCamp | 138 | 176.3 | classic, evergreen |
| 16 | An Introduction to Interactive Programming in Python | Coursera | 121 | 174.2 | classic, evergreen |
| 17 | 18.06 Linear Algebra (Gilbert Strang) | MIT OpenCourseWare | 105 | 169.9 | classic, evergreen |
| 18 | CS231n: Convolutional Neural Networks for Visual Recognition | Stanford University | 134 | 168.6 | classic, evergreen |
| 19 | 6.001 Structure and Interpretation of Computer Programs | MIT OpenCourseWare | 77 | 144.4 | classic, evergreen |
| 20 | Automate the Boring Stuff with Python | Udemy | 117 | 137.9 | - |
| 21 | CS61A: Structure and Interpretation of Computer Programs | UC Berkeley | 73 | 135.6 | classic, evergreen |
| 22 | 6.0001 Introduction to Computer Science and Programming in Python | MIT OCW | 86 | 127.3 | classic, evergreen |
| 23 | CS50's Web Programming with Python and JavaScript | edX | 103 | 121.9 | classic, evergreen |
| 24 | The Complete JavaScript Course: Build a Real-World Project | Udemy | 110 | 121.5 | rising |
| 25 | JavaScript and jQuery | Codecademy | 77 | 110.1 | classic, evergreen |
