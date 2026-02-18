# Knowledge Base — Master Guide

**Purpose:** Explains which files to use, how they connect, and how to inject them into the lesson generation prompt.

---

## The KB Stack (4 Files)

These four files form your complete knowledge base. Attach all four when generating lessons.

| # | File | Role | What It Controls |
|---|------|------|------------------|
| 1 | `NCERT_Pedagogical_Style_Knowledge.md` | **Pedagogical rules** | Teaching style, tone, Bloom's framework, opening structure, feedback rules, visual directions, constraints |
| 2 | `language_guidelines.md` | **Language calibration** | Sentence length, vocabulary limits, question complexity, instruction verbs, audio delivery — all per grade |
| 3 | `digital_interactions.md` | **Interaction constraints** | Which tap/drag/match/audio interactions are allowed per grade, Bloom's × interaction mapping, subject recommendations |
| 4 | `question_bank.md` | **Quiz design** | Question types with Bloom's tags, feedback templates, grade-level quiz distribution, output format |

### Optional reference file (attach only when the topic exists in it):
| 5 | `definitions_and_examples.md` | **Concept definitions** | Authoritative definitions, required examples, common misconceptions per topic |

---

## How the Files Connect

```
User Input: "Grade 3, EVS, Types of Plants"
                │
                ▼
┌─────────────────────────────────────────┐
│  NCERT_Pedagogical_Style_Knowledge.md   │
│  → Sets overall teaching rules          │
│  → Bloom's ceiling: Grade 3 = L1–L4    │
│    freely, L5 in 1–2 questions          │
│  → Opening: Greet → Connect → Preview   │
│    → Invite                             │
│  → Feedback: warm + reasoning-based     │
│  → Visual directions: structured format │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  language_guidelines.md                 │
│  → Grade 3 rules:                       │
│    Max 10–12 words per sentence         │
│    5–6 new words per lesson             │
│    "because" and "when" clauses allowed │
│    "Why?" with 1–2 sentence answers     │
│    Instruction verbs: Classify, Group,  │
│    Explain, Give a reason               │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  digital_interactions.md                │
│  → Grade 3 allowed: 15 types           │
│    Best fit for EVS classification:     │
│    Drag to Sort (L3 Apply)             │
│    Choose Odd One Out (L2/L4)          │
│    Match one to another (L2)           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  question_bank.md                       │
│  → Grade 3 quiz distribution:           │
│    L1: 2, L2: 3, L3: 3, L4: 1, L5: 1  │
│  → Types: Understanding + Application   │
│    + Matching + Fill + Yes/No Reasoning  │
│  → Feedback templates per type          │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  definitions_and_examples.md (optional) │
│  → Grade 3 EVS "Types of Plants":      │
│    Tree = tall, one thick trunk         │
│    Shrub = medium, many woody stems     │
│    Herb = small, soft green stems       │
│  → Required examples: Mango, Neem, etc.│
│  → Misconception: "all small plants     │
│    are herbs"                           │
└─────────────────────────────────────────┘
```

---

## Files NOT in the KB (and Why)

### `session_flow_templates.md` — Use for QA, not generation

This file contains 9 worked-out lesson examples for Grade K/1 maths (sorting by colour, size, shape, etc.). 

**Why not KB:** It's examples, not rules. If fed to the model as KB, it will copy the "Ria" character, the exact phrasing, and the kindergarten sorting format into every lesson — even Grade 4 EVS or Grade 3 English lessons.

**How to use instead:**
- Compare generated outputs against these templates to check quality
- Extract good feedback patterns and verify they match the question_bank templates
- Use as onboarding material for new team members to understand the desired lesson format

### `curriculum_topics.md` — Split and inject dynamically

This file is 4000+ lines covering all 272 topics across Grades K–4. It's too large to attach as a full KB file.

**How to use instead:**
- Build a lookup system that extracts only the relevant grade + subject + chapter section
- Inject that section into the user input (not as a KB file) at generation time
- Clean up by removing all "Examples from Context" lines (auto-extracted keywords, not useful)
- The topic_id values are useful for cross-referencing if you build a pipeline

### `grade_k_language_guidelines.md` — Replaced

This file was misnamed. It contained curriculum topic lists, not language guidelines. Its content is covered by `curriculum_topics.md`. The real language guidelines are now in `language_guidelines.md`.

**Action:** Delete this file or rename to `curriculum_grade_k.md` if you split the curriculum file.

---

## Prompt Integration

### Where to Reference KB Files in Your Prompt

Update the prompt's KB instruction block to:

```
You MUST use the following Knowledge Base files when generating lessons:

1. NCERT_Pedagogical_Style_Knowledge.md
   → Follow all pedagogical rules, Bloom's framework, opening
     structure, feedback rules, and visual direction format.

2. language_guidelines.md
   → Apply the target grade's sentence length limits, vocabulary
     rules, question type constraints, and instruction language.
   → This is the FINAL AUTHORITY on language complexity.

3. digital_interactions.md
   → Select ONLY interaction types allowed for the target grade.
   → Match interaction Bloom's level to the lesson section's
     target level.

4. question_bank.md
   → Use the Bloom's distribution table for the target grade.
   → Follow the feedback templates for each question type.
   → Tag every quiz question with its Bloom's level.

5. definitions_and_examples.md (when available for the topic)
   → Use the authoritative definitions as the basis for
     "Teacher explains" lines.
   → Use the required examples in activities and explanations.
   → Address at least one listed misconception in Doubts Item 3.
```

### Updated Prompt Reference for Phase 1 (Planner)

```
PHASE 1 — PEDAGOGICAL PLANNER (INTERNAL)

1. Extract target grade (default: Grade 3 if unspecified).
2. Load grade constraints from language_guidelines.md.
3. Identify 2–4 core concepts from the input context.
4. Write short grade-calibrated definitions using
   definitions_and_examples.md (if topic exists) or
   generate following NCERT style.
5. Add 1 real-life connection.
6. Select 3–5 grade-appropriate vocabulary terms within
   the grade's "new words per lesson" limit.
7. Choose 1 interaction type allowed for the grade from
   digital_interactions.md, matching the Bloom's level
   needed for the activity section (L3 Apply).
8. Identify 2 common misconceptions (from definitions file
   or inferred from content).
9. Plan 10 quiz questions following the Bloom's distribution
   from question_bank.md for the target grade.
10. Tag each planned question with Bloom's level and
    question type.
11. Plan the Opening Narration following the 4-beat
    structure from NCERT file (Greet → Connect → Preview
    → Invite).
12. If story characters exist in the input context, plan
    how to reference them in Line 2 (Connect).
```

---

## Checklist Before Going Live

- [ ] All 4 core KB files are attached to the model
- [ ] `session_flow_templates.md` is NOT attached as KB
- [ ] `grade_k_language_guidelines.md` is removed or renamed
- [ ] `curriculum_topics.md` is split by grade or injected dynamically
- [ ] The prompt references all 4 KB files by name
- [ ] The prompt's Phase 1 planner includes Bloom's distribution planning
- [ ] The prompt's output structure includes `Bloom's Level:` in quiz format
- [ ] Hardcoded subject-specific content (e.g., "Plants given: Mango...") is moved from system prompt to user input
- [ ] The wordsearch requirement is replaced with "Odd One Out" or "Sort the List"
