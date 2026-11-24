"""
Ultra-Crisp, Fast-Reading Question Bank for 2-Minute Assessment.
Designed for 8-10 second reading per question (mobile-optimized).
- Questions: 8-14 words max.
- Options: 2-6 words max.
"""

import random
import re

# Domain normalization keywords
DOMAIN_MAPPINGS = [
    (
        "tech",
        [
            "software", "tech", "computer", "it ", "information technology",
            "developer", "development", "engineer", "programming", "cloud",
            "devops", "web", "frontend", "backend", "fullstack", "qa", "cyber", "security"
        ],
    ),
    (
        "data",
        [
            "data", "analytics", "statistic", "machine learning", "ai", "artificial intelligence",
            "business intelligence", "bi", "big data", "deep learning"
        ],
    ),
    (
        "business_sales",
        [
            "sales", "marketing", "business development", "digital marketing", "seo",
            "advertising", "growth", "client", "commercial", "retail", "brand", "pr"
        ],
    ),
    (
        "finance",
        [
            "finance", "banking", "account", "tax", "audit", "wealth", "insurance",
            "investment", "fintech", "payroll"
        ],
    ),
    (
        "operations_hr",
        [
            "operation", "supply chain", "logistic", "human resource", "hr",
            "talent", "recruitment", "procurement", "inventory", "admin"
        ],
    ),
]


def classify_domain(domain_str: str) -> str:
    """Classifies a user-selected domain/industry into one of the specialized buckets."""
    d = (domain_str or "").lower()
    for bucket_key, keywords in DOMAIN_MAPPINGS:
        if any(k in d for k in keywords):
            return bucket_key
    return "general"


def classify_tier(experience_level: str) -> str:
    """Classifies candidate's experience level into fresher, junior, mid, or senior."""
    l = (experience_level or "").lower()
    if any(k in l for k in ("student", "fresher", "no experience", "intern")):
        return "fresher"
    if any(k in l for k in ("senior", "lead", "manager", "head", "expert", "director")):
        return "senior"
    nums = [int(n) for n in re.findall(r"\d+", l)]
    if nums:
        lo = min(nums)
        if lo == 0:
            return "fresher"
        if lo <= 2:
            return "junior"
        if lo <= 6:
            return "mid"
        return "senior"
    if "mid" in l:
        return "mid"
    if "junior" in l or "entry" in l:
        return "junior"
    return "fresher"


# ---------------------------------------------------------------------------
# UNIVERSAL POOL (Short & Crisp)
# ---------------------------------------------------------------------------

UNIVERSAL_POOL = {
    "fresher": {
        "IQ & Logic": [
            {
                "question": "What comes next in the series: 2, 6, 12, 20, 30, __?",
                "options": ["36", "40", "42", "48"],
                "correct_answer": "42",
            },
            {
                "question": "Which item does not belong: Mouse, Keyboard, Monitor, Spreadsheet?",
                "options": ["Mouse", "Keyboard", "Monitor", "Spreadsheet"],
                "correct_answer": "Spreadsheet",
            },
            {
                "question": "Complete the sequence: 3, 9, 27, 81, __?",
                "options": ["162", "243", "324", "180"],
                "correct_answer": "243",
            },
            {
                "question": "Book is to Reading as Fork is to __?",
                "options": ["Cooking", "Eating", "Serving", "Kitchen"],
                "correct_answer": "Eating",
            },
            {
                "question": "If all roses are flowers and some flowers fade, what is true?",
                "options": ["Some flowers are roses", "All roses fade quickly", "No roses fade", "Roses never fade"],
                "correct_answer": "Some flowers are roses",
            },
        ],
        "Aptitude": [
            {
                "question": "One person takes 6 hours. How long do two people take?",
                "options": ["6 hours", "4 hours", "3 hours", "12 hours"],
                "correct_answer": "3 hours",
            },
            {
                "question": "You read 30 pages a day. How long to finish 120 pages?",
                "options": ["3 days", "4 days", "5 days", "6 days"],
                "correct_answer": "4 days",
            },
            {
                "question": "A ₹500 product has a 20% discount. What is the price?",
                "options": ["₹400", "₹450", "₹380", "₹420"],
                "correct_answer": "₹400",
            },
            {
                "question": "You travel 150 km in 3 hours. How far in 5 hours?",
                "options": ["250 km", "225 km", "300 km", "200 km"],
                "correct_answer": "250 km",
            },
        ],
        "Psychological": [
            {
                "question": "How do you prefer to learn new concepts in {domain}?",
                "options": ["Practice and learn from errors", "Watch tutorials and read guides", "Ask a mentor to explain", "Follow step-by-step templates"],
            },
            {
                "question": "Which type of work motivates you most?",
                "options": ["Solving clear tangible problems", "Communicating with clients", "Organizing information clearly", "Improving existing processes"],
            },
            {
                "question": "A mentor criticizes your first project draft. What do you do?",
                "options": ["Ask questions and improve draft", "Defend my original draft", "Feel discouraged and stop", "Agree politely but ignore"],
            },
        ],
        "Leadership": [
            {
                "question": "You spot a mistake in work you already shared. What do you do?",
                "options": ["Notify team and fix immediately", "Wait to see if noticed", "Blame the initial instructions", "Delete work without telling"],
            },
            {
                "question": "A teammate is struggling with project deadlines. How do you respond?",
                "options": ["Offer to take a task", "Complain to the team manager", "Wait for them to fail", "Do their entire work silently"],
            },
            {
                "question": "Which role fits your team style best?",
                "options": ["Keeping project milestones on track", "Solving the hardest technical problems", "Connecting team members' ideas", "Polishing and improving quality"],
            },
        ],
        "Decision Making": [
            {
                "question": "A task brief is unclear and due tomorrow. What do you do?",
                "options": ["Ask manager for quick clarification", "Guess and work without asking", "Wait until next team meeting", "Pass task to someone else"],
            },
            {
                "question": "Two seniors give conflicting advice on a task. What do you do?",
                "options": ["Discuss with manager to align", "Follow the first senior", "Ignore both and do own way", "Pick whichever is easiest"],
            },
            {
                "question": "A shortcut saves an hour but skips a check. What do you do?",
                "options": ["Do check and warn of delay", "Skip check to finish fast", "Test only if issues happen", "Wait for someone to notice"],
            },
        ],
    },
    "junior": {
        "IQ & Logic": [
            {
                "question": "What number comes next: 4, 7, 12, 19, 28, __?",
                "options": ["39", "37", "40", "42"],
                "correct_answer": "39",
            },
            {
                "question": "Managers approve reports. Neha does not approve reports. What follows?",
                "options": ["Neha is not a manager", "Neha is a new manager", "Neha writes reports instead", "Neha will become manager"],
                "correct_answer": "Neha is not a manager",
            },
            {
                "question": "Blueprint is to Building as Algorithm is to __?",
                "options": ["Program", "Hardware", "Network", "Database"],
                "correct_answer": "Program",
            },
            {
                "question": "In a line of 25 people, Rohan is 9th from front. His position from back?",
                "options": ["17th", "16th", "18th", "15th"],
                "correct_answer": "17th",
            },
        ],
        "Aptitude": [
            {
                "question": "A server handles 300 requests/minute. How many in 15 minutes?",
                "options": ["4,500", "4,200", "5,000", "3,800"],
                "correct_answer": "4,500",
            },
            {
                "question": "A 40-hour task ended up taking 50 hours. What was the percentage delay?",
                "options": ["25%", "20%", "15%", "30%"],
                "correct_answer": "25%",
            },
            {
                "question": "Four 45-minute meetings with 15-minute buffers between them. Total time?",
                "options": ["3 hours 45 mins", "3 hours 30 mins", "4 hours", "3 hours 15 mins"],
                "correct_answer": "3 hours 45 mins",
            },
        ],
        "Psychological": [
            {
                "question": "An urgent blocker appears during a deadline task. What do you do?",
                "options": ["Triage blocker and update timeline", "Drop deadline work silently", "Ignore blocker until task done", "Wait for manager instruction"],
            },
            {
                "question": "How do you stay engaged during routine repetitive work?",
                "options": ["Automate and document the workflow", "Rush through to finish fast", "Delay work until last minute", "Ask juniors to do it"],
            },
        ],
        "Leadership": [
            {
                "question": "A new joiner struggles with project setup. What do you do?",
                "options": ["Help them and update docs", "Tell them to self-learn", "Escalate delay to management", "Ignore and continue own work"],
            },
            {
                "question": "What makes an individual contributor most valuable on a team?",
                "options": ["Reliable delivery and open communication", "Working isolated without team sync", "Only doing bare minimum tasks", "Blindly agreeing with everyone"],
            },
        ],
        "Decision Making": [
            {
                "question": "Choose between a 2-hour temporary hack vs a 2-day clean solution. Deadline is next week.",
                "options": ["Build clean solution to avoid debt", "Always choose the quick hack", "Postpone decision to deadline", "Ask another team to build"],
            },
            {
                "question": "A stakeholder requests urgent ad-hoc work during an active sprint. What do you do?",
                "options": ["Check priority with product owner", "Drop sprint tasks immediately", "Decline bluntly without explanation", "Promise instant delivery blindly"],
            },
        ],
    },
    "mid": {
        "IQ & Logic": [
            {
                "question": "What is the next number in sequence: 10, 18, 34, 66, 130, __?",
                "options": ["258", "256", "260", "248"],
                "correct_answer": "258",
            },
            {
                "question": "All Cluster A services have failover. Service X has no failover. What follows?",
                "options": ["Service X not in Cluster A", "Service X is failing", "Cluster A is broken", "Service X is database"],
                "correct_answer": "Service X not in Cluster A",
            },
            {
                "question": "5 engineers write 5 test suites in 5 hours. How long for 10 engineers for 10 suites?",
                "options": ["5 hours", "10 hours", "2.5 hours", "1 hour"],
                "correct_answer": "5 hours",
            },
        ],
        "Aptitude": [
            {
                "question": "Query response slowed from 120ms to 480ms. What is the slowdown factor?",
                "options": ["4x slower", "3x slower", "2.5x slower", "5x slower"],
                "correct_answer": "4x slower",
            },
            {
                "question": "Downsizing from 8 servers to 5 servers at ₹45/hr saves how much monthly (720 hrs)?",
                "options": ["₹97,200", "₹85,000", "₹1,08,000", "₹72,000"],
                "correct_answer": "₹97,200",
            },
            {
                "question": "Team capacity is 80 points with 85% delivery rate. What points to commit?",
                "options": ["68 points", "80 points", "75 points", "85 points"],
                "correct_answer": "68 points",
            },
        ],
        "Psychological": [
            {
                "question": "A critical production incident strikes under customer eyes. What is your priority?",
                "options": ["Stabilize system and update stakeholders", "Apply unverified hotfixes in prod", "Blame teammate who made commit", "Mute alerts and wait out"],
            },
            {
                "question": "Management requests a feature that harms long-term system stability. How do you respond?",
                "options": ["Explain business risk of technical debt", "Reject flatly without alternatives", "Accept silently and let it break", "Complain to peers privately"],
            },
        ],
        "Leadership": [
            {
                "question": "Two senior peers disagree on framework choice. How do you resolve?",
                "options": ["Build evaluation matrix on trade-offs", "Pick whichever senior has more tenure", "Tell them to fight it out", "Escalate to VP immediately"],
            },
            {
                "question": "A junior repeatedly submits flawed pull requests. What is the best coaching step?",
                "options": ["Pair program and set checklist", "Reject PRs with harsh remarks", "Write their code yourself", "Ask to remove them from team"],
            },
        ],
        "Decision Making": [
            {
                "question": "A feature fails latency thresholds two weeks before launch. What do you do?",
                "options": ["Profile bottleneck and present options", "Ship anyway and wait for complaints", "Cancel launch without investigation", "Turn off monitoring alerts"],
            },
            {
                "question": "Deciding between building an in-house tool vs buying SaaS. What is primary?",
                "options": ["Total cost, maintenance, and security", "Always build in-house for pride", "Always buy external SaaS", "Pick newest tech stack"],
            },
        ],
    },
    "senior": {
        "IQ & Logic": [
            {
                "question": "Throughput drops 20% while latency quadruples under double load. What is the cause?",
                "options": ["Resource contention on bottleneck", "Normal linear scaling behavior", "Client bandwidth saturation", "Sub-millisecond cache efficiency"],
                "correct_answer": "Resource contention on bottleneck",
            },
            {
                "question": "In a 7-node quorum cluster, what is the maximum simultaneous node failures tolerated?",
                "options": ["3 nodes", "2 nodes", "4 nodes", "1 node"],
                "correct_answer": "3 nodes",
            },
            {
                "question": "Three independent services each have 99% uptime. What is their combined serial uptime?",
                "options": ["~97.0%", "~99.0%", "~98.5%", "~99.9%"],
                "correct_answer": "~97.0%",
            },
        ],
        "Aptitude": [
            {
                "question": "60 engineers have 15% annual attrition. If replacement costs ₹12L each, total annual cost?",
                "options": ["₹1.08 Crore", "₹90 Lakhs", "₹1.20 Crore", "₹72 Lakhs"],
                "correct_answer": "₹1.08 Crore",
            },
            {
                "question": "Cloud migration saves ₹1.3L/month with a ₹7.8L upfront cost. What is the payback period?",
                "options": ["6 months", "8 months", "10 months", "12 months"],
                "correct_answer": "6 months",
            },
            {
                "question": "A 45-minute outage affects 80,000 users with ₹15 loss per user-hour. Direct loss?",
                "options": ["₹9,00,000", "₹12,00,000", "₹15,00,000", "₹6,00,000"],
                "correct_answer": "₹9,00,000",
            },
        ],
        "Psychological": [
            {
                "question": "Executives push for unrealistic deadlines risking team burnout. How do you lead?",
                "options": ["Negotiate phased roadmap with data", "Force mandatory 80-hour workweeks", "Promise everything and make excuses", "Quit without addressing problem"],
            },
            {
                "question": "How do you build high psychological safety across engineering teams?",
                "options": ["Reward blameless post-mortems", "Publicly reprimand failed attempts", "Keep decisions in closed circles", "Suppress all dissenting opinions"],
            },
        ],
        "Leadership": [
            {
                "question": "Engineering wants refactoring while product wants new features. How do you balance?",
                "options": ["Allocate fixed sprint budget for tech debt", "Give features 100% of capacity", "Halt all feature work for a year", "Let the conflict stall work"],
            },
            {
                "question": "How do you best mentor high-potential leads for executive growth?",
                "options": ["Delegate strategic initiatives with guidance", "Keep them on low-level tasks", "Micromanage every decision they take", "Treat them as career competition"],
            },
        ],
        "Decision Making": [
            {
                "question": "What principle best guides long-term enterprise architecture in {domain}?",
                "options": ["Modular boundaries and reversible choices", "Lock in the most complex stack", "Build rigid tightly coupled monolith", "Avoid documentation and ADRs"],
            },
            {
                "question": "During a critical security vulnerability discovery, what is your first command step?",
                "options": ["Isolate blast radius and mobilize response", "Conceal breach from security teams", "Shut down all servers with no backup", "Wait for media coverage first"],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# SPECIALIZED ROLE-SPECIFIC QUESTIONS (Short & Crisp)
# ---------------------------------------------------------------------------

ROLE_SPECIFIC_QUESTIONS = {
    "tech": {
        "fresher": {
            "Aptitude": [
                {
                    "question": "Debugging takes 40 mins and coding takes 20 mins. Percentage spent debugging?",
                    "options": ["66.7%", "50%", "33.3%", "75%"],
                    "correct_answer": "66.7%",
                },
            ],
            "Decision Making": [
                {
                    "question": "Your code passed local tests, but breaks the team's build. What do you do?",
                    "options": ["Investigate diff and assist rollback", "Say it works on my machine", "Ignore until tomorrow's standup", "Close bug without verification"],
                },
            ],
        },
        "junior": {
            "Aptitude": [
                {
                    "question": "An API returns 50 items/page. How many pages to fetch 820 items?",
                    "options": ["17 pages", "16 pages", "18 pages", "15 pages"],
                    "correct_answer": "17 pages",
                },
            ],
            "Leadership": [
                {
                    "question": "A query lacks an index and slows down all users. What do you do?",
                    "options": ["Benchmark, test index, and deploy", "Complain in team chat", "Ignore since not your ticket", "Restart server during workday"],
                },
            ],
        },
        "mid": {
            "Decision Making": [
                {
                    "question": "REST vs Message Queue for payment notifications. What decides?",
                    "options": ["Traffic spike resilience and retries", "REST is easier to inspect", "Queue is always better", "Whichever is newer"],
                },
            ],
        },
        "senior": {
            "Decision Making": [
                {
                    "question": "Designing cross-region database failover with zero data loss. What is the trade-off?",
                    "options": ["Higher write latency for replication", "OS memory usage differences", "Dashboard styling options", "Firewall open port counts"],
                },
            ],
        },
    },
    "data": {
        "fresher": {
            "IQ & Logic": [
                {
                    "question": "Nine values are near 15, but one value is 500. Which metric is most distorted?",
                    "options": ["Mean (Average)", "Median", "Mode", "Count"],
                    "correct_answer": "Mean (Average)",
                },
            ],
            "Aptitude": [
                {
                    "question": "Quarterly sales are ₹40K, ₹60K, ₹50K, ₹90K. What is the average?",
                    "options": ["₹60,000", "₹55,000", "₹65,000", "₹50,000"],
                    "correct_answer": "₹60,000",
                },
            ],
        },
        "junior": {
            "Decision Making": [
                {
                    "question": "12% of customer rows have missing values. How do you handle them?",
                    "options": ["Analyze pattern and impute appropriately", "Delete all rows with missing values", "Write 'Unknown' everywhere blindly", "Ignore and run models anyway"],
                },
            ],
        },
        "mid": {
            "Aptitude": [
                {
                    "question": "A model has 700 True Positives and 80 False Positives. What is Precision?",
                    "options": ["89.7%", "85.0%", "92.5%", "78.0%"],
                    "correct_answer": "89.7%",
                },
            ],
        },
        "senior": {
            "Leadership": [
                {
                    "question": "Leadership wants an AI hiring model live in 2 weeks. What is your chief action?",
                    "options": ["Audit algorithmic bias and privacy first", "Deploy immediately to hit deadline", "Refuse without constructive plan", "Hand accountability to an intern"],
                },
            ],
        },
    },
    "business_sales": {
        "fresher": {
            "Aptitude": [
                {
                    "question": "An ad gets 2,000 clicks from 50,000 views. What is Click-Through Rate?",
                    "options": ["4.0%", "2.5%", "5.0%", "1.0%"],
                    "correct_answer": "4.0%",
                },
                {
                    "question": "You convert 6 deals out of 30 client meetings. What is your conversion rate?",
                    "options": ["20%", "25%", "15%", "18%"],
                    "correct_answer": "20%",
                },
            ],
            "Psychological": [
                {
                    "question": "Prospects repeatedly reject your pitch on price. How do you respond?",
                    "options": ["Uncover pain points and show value", "Take offense and hang up", "Slash price 50% without approval", "Stop calling for the week"],
                },
            ],
        },
        "junior": {
            "Decision Making": [
                {
                    "question": "A key client threatens to leave over a delivery delay. What do you do?",
                    "options": ["Empathize and provide clear resolution roadmap", "Blame another team to save self", "Avoid client emails until fixed", "Argue that delay is minor"],
                },
            ],
        },
        "mid": {
            "Aptitude": [
                {
                    "question": "₹1.5L marketing spend gets 75 clients worth ₹18K each. What is LTV:CAC?",
                    "options": ["9:1", "6:1", "12:1", "3:1"],
                    "correct_answer": "9:1",
                },
            ],
        },
        "senior": {
            "Leadership": [
                {
                    "question": "Quarterly sales face a 20% deficit. How do you lead your team?",
                    "options": ["Refocus on high-margin target accounts", "Demand double blind cold calls", "Panic in public company chat", "Fire regional leads abruptly"],
                },
            ],
        },
    },
    "finance": {
        "fresher": {
            "Aptitude": [
                {
                    "question": "Assets are ₹8L and liabilities are ₹4L. What is the Current Ratio?",
                    "options": ["2.0", "1.5", "0.5", "2.5"],
                    "correct_answer": "2.0",
                },
                {
                    "question": "₹50,000 deposited at 8% simple interest for 3 years. Total interest earned?",
                    "options": ["₹12,000", "₹10,000", "₹15,000", "₹8,000"],
                    "correct_answer": "₹12,000",
                },
            ],
            "Decision Making": [
                {
                    "question": "An expense report lacks an official GST bill. What do you do?",
                    "options": ["Request invoice before approving payment", "Approve anyway since friend submitted", "Report employee for fraud immediately", "Fake a receipt to close task"],
                },
            ],
        },
        "junior": {
            "Aptitude": [
                {
                    "question": "Revenue ₹25L, Cost of Goods ₹15L, operating costs ₹4L. Operating profit?",
                    "options": ["₹6 Lakhs", "₹10 Lakhs", "₹4 Lakhs", "₹8 Lakhs"],
                    "correct_answer": "₹6 Lakhs",
                },
            ],
        },
        "mid": {
            "Decision Making": [
                {
                    "question": "You spot an unexplained ₹3.5L gap in vendor suspense balance. What do you do?",
                    "options": ["Trace ledgers and alert Finance Controller", "Book as miscellaneous to balance", "Wait for annual audit to notice", "Delete suspense ledger lines"],
                },
            ],
        },
        "senior": {
            "Leadership": [
                {
                    "question": "Deciding between market expansion vs paying corporate debt. What guides you?",
                    "options": ["Compare IRR, cost of capital, and cash flow", "Pick whichever manager speaks loudest", "Lock all cash in zero-interest accounts", "Spend reserves on executive bonuses"],
                },
            ],
        },
    },
    "operations_hr": {
        "fresher": {
            "Aptitude": [
                {
                    "question": "5 staff pack 450 packages in 3 hours. How many will 10 staff pack?",
                    "options": ["900 packages", "750 packages", "1,200 packages", "600 packages"],
                    "correct_answer": "900 packages",
                },
            ],
            "Psychological": [
                {
                    "question": "Multiple managers ask for tasks at once. How do you organize?",
                    "options": ["Prioritize by urgency and communicate ETAs", "Do task for whoever yells loudest", "Ignore all and work on random item", "Block calendar and decline all"],
                },
            ],
        },
        "junior": {
            "Decision Making": [
                {
                    "question": "An employee reports supervisor bullying in confidence. What do you do?",
                    "options": ["Document objectively and start grievance process", "Tell employee to tolerate supervisor", "Confront supervisor publicly right away", "Dismiss complaint as workplace gossip"],
                },
            ],
        },
        "mid": {
            "Aptitude": [
                {
                    "question": "Inventory cycle drops from 45 to 30 days for ₹60L stock. Freed capital?",
                    "options": ["₹20 Lakhs", "₹15 Lakhs", "₹25 Lakhs", "₹10 Lakhs"],
                    "correct_answer": "₹20 Lakhs",
                },
            ],
        },
        "senior": {
            "Leadership": [
                {
                    "question": "Leading organizational restructuring across departments. What is your priority?",
                    "options": ["Transparent communication and employee dignity", "Mass email layoffs on Friday night", "Deny rumors while letting them spread", "Refuse to adjust despite budget deficit"],
                },
            ],
        },
    },
}


def get_curated_question_plan(domain_interest: str, experience_level: str) -> list[dict]:
    """Selects 10 ultra-crisp, level- and domain-matched questions."""
    domain_key = classify_domain(domain_interest)
    tier_key = classify_tier(experience_level)
    domain_label = (domain_interest or "your chosen field").strip() or "your chosen field"

    categories = [
        ("IQ & Logic", 2),
        ("Aptitude", 2),
        ("Psychological", 2),
        ("Leadership", 2),
        ("Decision Making", 2),
    ]

    selected_by_cat: dict[str, list[dict]] = {}

    for cat_name, count in categories:
        candidates: list[dict] = []

        # 1. Specialized domain pool
        role_pool = (
            ROLE_SPECIFIC_QUESTIONS.get(domain_key, {})
            .get(tier_key, {})
            .get(cat_name, [])
        )
        candidates.extend(role_pool)

        # 2. Universal pool for this tier
        universal_pool = (
            UNIVERSAL_POOL.get(tier_key, {})
            .get(cat_name, [])
        )
        candidates.extend(universal_pool)

        # 3. Fallback to fresher pool if needed
        if len(candidates) < count:
            fallback_pool = UNIVERSAL_POOL.get("fresher", {}).get(cat_name, [])
            candidates.extend(fallback_pool)

        # Sample required count randomly
        chosen = random.sample(candidates, min(count, len(candidates)))

        formatted_items = []
        for item in chosen:
            q_text = item["question"].replace("{domain}", domain_label)
            raw_options = [opt.replace("{domain}", domain_label) for opt in item["options"]]

            # Shuffle options
            shuffled_options = list(raw_options)
            random.shuffle(shuffled_options)

            entry = {
                "category": cat_name,
                "question": q_text,
                "options": shuffled_options,
            }
            if "correct_answer" in item:
                entry["correct_answer"] = item["correct_answer"].replace("{domain}", domain_label)

            formatted_items.append(entry)

        selected_by_cat[cat_name] = formatted_items

    # Interleave categories across 2 rounds
    ordered_plan: list[dict] = []
    for round_idx in range(2):
        for cat_name, _ in categories:
            items = selected_by_cat.get(cat_name, [])
            if round_idx < len(items):
                ordered_plan.append(items[round_idx])

    return ordered_plan[:10]
