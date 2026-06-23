"""A tiny synthetic eval set for the decontamination demos.

These are representative eval-style questions written for the demo (NOT copied from any
real benchmark), plus reworded paraphrases of a subset. They let the decontamination
scripts inject controlled "contamination" into a corpus and show that n-gram overlap
catches verbatim copies while a fuzzy pass is needed for paraphrases.
"""

from __future__ import annotations

EVAL_ITEMS: dict[str, str] = {
    "gsm8k_1": "If a train travels 60 miles in 90 minutes, what is its average speed in miles per hour?",
    "gsm8k_2": "A baker has 24 cookies and packs them into boxes of 6. How many boxes can the baker fill?",
    "mmlu_air": "Which gas makes up the largest proportion of Earth's atmosphere by volume?",
    "mmlu_moon": "In which year did the first human land on the Moon?",
    "mmlu_atp": "What is the powerhouse organelle of the eukaryotic cell that produces ATP?",
    "trivia_syd": "What is the capital city of the country whose largest city is Sydney?",
    "sci_salt": "What two elements combine to form ordinary table salt?",
    "math_prime": "What is the smallest prime number greater than twenty?",
    "code_fib": "Write a Python function that returns the nth Fibonacci number using recursion.",
    "hist_machu": "Which ancient civilization built the Machu Picchu citadel in the Andes mountains?",
    "geo_river": "Which is the longest river in the world by total length?",
    "phys_newton": "What physical quantity is measured in units of newtons?",
}

# Reworded versions of a subset — share no long n-gram with the originals, so n-gram
# decontamination misses them and the fuzzy pass is required.
PARAPHRASES: dict[str, str] = {
    "gsm8k_1": "Suppose a train covers sixty miles over the course of an hour and a half; how fast is it going in mph?",
    "mmlu_air": "By volume, which gas is the most abundant component of the air surrounding our planet?",
    "trivia_syd": "Name the capital of the nation whose biggest city happens to be Sydney.",
    "math_prime": "Identify the least prime number that is larger than the value twenty.",
    "code_fib": "Implement a recursive Python routine that computes the Fibonacci number at index n.",
    "geo_river": "Across the whole globe, which river stretches the longest from its source to its mouth?",
}
