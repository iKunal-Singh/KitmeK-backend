"""Canonical fixture lesson dictionaries for KitmeK validator and API tests.

Each constant represents a complete lesson JSON payload shaped like the output
from Claude's generation step (Section 5.1 of the architecture document).

NOTE: The actual ValidationPipeline uses ``_extract_all_text`` which
recursively joins ALL string values in the lesson dict with spaces, then
sentence-splits on ``.!?``.  This means non-prose fields (type, bloom_level,
option text, layout, etc.) are also scanned for word-count limits.  Fixtures
are designed to work with this behaviour:
  - All string values that do not end with a sentence terminator are kept
    ≤ 4 words so that the concatenated "sentence" stays within Grade 3's
    12-word ceiling.
  - Quiz options are single words where possible.
  - Top-level metadata keys (grade, subject, chapter, topic) are omitted
    because they are DB metadata, not part of the Claude JSON output schema.

Bloom's distribution for Grade 3 quiz (10 questions):
    L1 × 2, L2 × 3, L3 × 3, L4 × 1, L5 × 1
Language ceiling Grade 3: max 12 words per sentence, ≤ 6 new vocab words.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# VALID_GRADE3_LESSON — passes ALL 8 validation checks
# ---------------------------------------------------------------------------

VALID_GRADE3_LESSON: dict = {
    # No top-level grade/subject/chapter/topic keys — those come from the DB,
    # not from Claude's JSON output (Architecture Section 5.1).
    "learning_objective": (
        "Students will identify trees and shrubs by stem features."
    ),
    "opening_narration": {
        "line_1": "Good morning, children. [Beat]",
        "line_2": "Have you seen plants in your garden? [Beat]",
        "line_3": "Today we learn about trees and shrubs. [Pause]",
        "line_4": "Let us begin with [Emphasis: trees].",
    },
    "on_screen_opening": {
        "layout": "split",
        "static_elements": ["tree", "shrub"],
        "interactive_elements": [],
        "animation": "fade",
    },
    "narrated_explanation": [
        {
            "concept_name": "Trees",
            "teacher_explains": (
                "A [Emphasis: tree] has one thick woody trunk. "
                "It grows tall for many years. [Pause]"
            ),
            "bloom_level": "L1",
            "on_screen": {"image": "mango"},
            "transition": "Now look at shrubs.",
        },
        {
            "concept_name": "Shrubs",
            "teacher_explains": (
                "A [Emphasis: shrub] has many woody stems near the ground. "
                "Shrubs are shorter than trees. [Beat]"
            ),
            "bloom_level": "L2",
            "on_screen": {"image": "rose"},
            "transition": "Spot the difference.",
        },
        {
            "concept_name": "Differences",
            "teacher_explains": (
                "Trees have one trunk, but shrubs have many stems. "
                "Look at the stem to know the type. [Beat]"
            ),
            "bloom_level": "L2",
            "on_screen": {"table": "tree-shrub"},
            "transition": "Now sort them yourself.",
        },
    ],
    "interactive_activity": {
        "type": "Drag to Sort",
        "bloom_level": "L3",
        "instructions": "Drag each plant to the right group.",
        "on_screen": {
            "items": ["Mango", "Rose", "Neem", "Jasmine"],
            "targets": ["Tree", "Shrub"],
        },
        "feedback_hint_1": "Look at the stems carefully. [Beat]",
        "feedback_hint_2": "Does it have one trunk or many stems?",
        "feedback_reveal": (
            "Mango and Neem are trees. Rose and Jasmine are shrubs."
        ),
    },
    "doubts_discussion": [
        {
            "question": "Can a small plant be a tree?",
            "bloom_level": "L2",
            "answer": "Yes, if it has one woody trunk.",
            "teacher_clarification": (
                "Size alone does not decide the type. Look at the stem. [Beat]"
            ),
        }
    ],
    "quick_quiz": [
        # L1 × 2
        {
            "question_number": 1,
            "type": "MCQ",
            "bloom_level": "L1",
            "prompt": "Which plant has one thick trunk?",
            "options": ["Tree", "Shrub", "Herb", "Climber"],
            "answer": "Tree",
            "feedback_correct": "Yes! Trees have one thick, woody trunk.",
            "feedback_incorrect": "Not quite. Trees have one thick trunk.",
        },
        {
            "question_number": 2,
            "type": "True/False",
            "bloom_level": "L1",
            "prompt": "A shrub has many woody stems near the ground.",
            "options": ["True", "False"],
            "answer": "True",
            "feedback_correct": "Correct! Shrubs grow many stems near the ground.",
            "feedback_incorrect": "Shrubs have many stems near the ground.",
        },
        # L2 × 3
        {
            "question_number": 3,
            "type": "MCQ",
            "bloom_level": "L2",
            "prompt": "Why does rose belong to the shrub group?",
            "options": ["Many stems", "One trunk", "No stem", "It climbs"],
            "answer": "Many stems",
            "feedback_correct": "Right! Rose is a shrub with many woody stems.",
            "feedback_incorrect": "Think again. How many stems does rose have?",
        },
        {
            "question_number": 4,
            "type": "Fill-blank",
            "bloom_level": "L2",
            "prompt": "A plant with many woody stems is called a ______.",
            "options": [],
            "answer": "Shrub",
            "feedback_correct": "Well done! Many woody stems near the ground means shrub.",
            "feedback_incorrect": "The answer is shrub. It has many woody stems.",
        },
        {
            "question_number": 5,
            "type": "MCQ",
            "bloom_level": "L2",
            "prompt": "Which of these is an example of a tree?",
            "options": ["Rose", "Neem", "Jasmine", "Mint"],
            "answer": "Neem",
            "feedback_correct": "Yes! Neem has one thick trunk so it is a tree.",
            "feedback_incorrect": "Look for the plant with one thick trunk.",
        },
        # L3 × 3
        {
            "question_number": 6,
            "type": "Scenario",
            "bloom_level": "L3",
            "prompt": "Riya found a plant with one thick trunk. What is it? [Beat]",
            "options": ["Tree", "Shrub", "Herb", "Climber"],
            "answer": "Tree",
            "feedback_correct": "Correct! One thick trunk means it is a tree.",
            "feedback_incorrect": "One thick trunk means it must be a tree.",
        },
        {
            "question_number": 7,
            "type": "MCQ",
            "bloom_level": "L3",
            "prompt": "A short plant with many woody stems is a ______.",
            "options": ["Tree", "Shrub", "Herb", "Climber"],
            "answer": "Shrub",
            "feedback_correct": "Right! Many woody stems near the ground means shrub.",
            "feedback_incorrect": "Many woody stems near the ground is a shrub.",
        },
        {
            "question_number": 8,
            "type": "MCQ",
            "bloom_level": "L3",
            "prompt": "Which feature helps us classify plants correctly?",
            "options": ["Stem type", "Leaf colour", "Height", "Flowers"],
            "answer": "Stem type",
            "feedback_correct": "Excellent! The stem type is the key feature.",
            "feedback_incorrect": "Check the stem type to classify correctly.",
        },
        # L4 × 1
        {
            "question_number": 9,
            "type": "MCQ",
            "bloom_level": "L4",
            "prompt": "How is a mango tree different from a rose plant?",
            "options": ["Trunk vs stems", "Colour", "Habitat", "Size"],
            "answer": "Trunk vs stems",
            "feedback_correct": "Well done! That is the key structural difference.",
            "feedback_incorrect": "Focus on the stem type, not colour or size.",
        },
        # L5 × 1
        {
            "question_number": 10,
            "type": "True/False",
            "bloom_level": "L5",
            "prompt": "True or false: Any tall plant must be a tree. Why? [Beat]",
            "options": ["True", "False"],
            "answer": "False",
            "feedback_correct": (
                "Correct! Height alone does not define a tree. "
                "Stem structure matters more."
            ),
            "feedback_incorrect": (
                "Reconsider. Some shrubs grow tall but still have many stems."
            ),
        },
    ],
    "conclusion": {
        "recap": (
            "Today we learned trees have one thick trunk. "
            "Shrubs have many woody stems."
        ),
        "real_life_connection": (
            "Look at plants near your home. Find a tree and a shrub. [Beat]"
        ),
        "reflection_prompt": "What would you call a plant with three woody stems?",
    },
}


# ---------------------------------------------------------------------------
# INVALID_LESSON_LONG_SENTENCES — fails language_ceiling check
# ---------------------------------------------------------------------------

INVALID_LESSON_LONG_SENTENCES: dict = {
    **VALID_GRADE3_LESSON,
    # Override narrated explanation with one sentence that has 25 words —
    # far exceeding Grade 3's ceiling of 12 words.
    "narrated_explanation": [
        {
            "concept_name": "Trees.",
            "teacher_explains": (
                # 25-word sentence (no audio markers to strip):
                "A tree is a very tall and strong and large and heavy and "
                "old and beautiful and important and useful and amazing plant "
                "that grows in every garden and forest around the world."
            ),
            "bloom_level": "L1.",
            "on_screen": {},
            "transition": "Now look at shrubs.",
        },
    ],
}


# ---------------------------------------------------------------------------
# INVALID_LESSON_WRONG_BLOOMS — fails blooms_distribution check
# ---------------------------------------------------------------------------

# All 10 quiz questions tagged L1 — but Grade 3 requires L1×2, L2×3, L3×3, L4×1, L5×1
_wrong_blooms_quiz = [
    {
        "question_number": i + 1,
        "type": "MCQ.",
        "bloom_level": "L1",  # All L1 — wrong distribution for Grade 3
        "prompt": f"Question {i + 1}?",
        "options": ["A", "B"],
        "answer": "A.",
        "feedback_correct": "Well done, that is correct.",
        "feedback_incorrect": "Not quite, try again please.",
    }
    for i in range(10)
]

INVALID_LESSON_WRONG_BLOOMS: dict = {
    **VALID_GRADE3_LESSON,
    "quick_quiz": _wrong_blooms_quiz,
}


# ---------------------------------------------------------------------------
# INVALID_LESSON_BAD_INTERACTION — fails interaction_type check
# ---------------------------------------------------------------------------

INVALID_LESSON_BAD_INTERACTION: dict = {
    **VALID_GRADE3_LESSON,
    "interactive_activity": {
        # "Scratch to reveal" is only allowed for Grade K, NOT Grade 3
        "type": "Scratch to reveal",
        "bloom_level": "L3",
        "instructions": "Scratch the card to reveal the answer.",
        "on_screen": {},
        "feedback_hint_1": "Try scratching gently.",
        "feedback_hint_2": "Keep going, almost there!",
        "feedback_reveal": "The answer is: it is a tree.",
    },
}


# ---------------------------------------------------------------------------
# INVALID_LESSON_MISSING_FEEDBACK — fails feedback_structure check
# ---------------------------------------------------------------------------

_quiz_no_feedback = [
    {
        "question_number": i + 1,
        "type": "MCQ.",
        "bloom_level": q["bloom_level"],
        "prompt": q["prompt"],
        "options": q.get("options", ["A", "B"]),
        "answer": q["answer"],
        # Deliberately omitting feedback_correct and feedback_incorrect
    }
    for i, q in enumerate(VALID_GRADE3_LESSON["quick_quiz"])
]

INVALID_LESSON_MISSING_FEEDBACK: dict = {
    **VALID_GRADE3_LESSON,
    "quick_quiz": _quiz_no_feedback,
}
