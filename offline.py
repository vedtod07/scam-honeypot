"""
offline.py - deterministic, LLM-free simulator for the persona and scammer roles.

Lets the whole pipeline (turn loop, extractor, guardrail, report, eval) run with
no API key. It is NOT a language model: the scammer reveals the script's planted
indicators on a fixed schedule and the persona draws from a pool of stall lines.
Occasionally the persona "slips" and tries to leak an OTP so the guardrail is
exercised for real. Results therefore measure the pipeline, not model quality.
"""

import random

STAGE_LINES = {
    "impersonation": [
        "I repeat, this is {identity}. Please listen carefully, sir.",
        "Sir, I am an authorised officer of {identity}. This call is recorded.",
    ],
    "fear_hook": [
        "Your case is already registered and action will start within the hour.",
        "If you do not cooperate, the matter will be escalated to the senior officer.",
    ],
    "isolation": [
        "Do not tell your family or anyone else about this call, it is confidential.",
        "Do not disconnect and do not speak to the bank branch, it will complicate your case.",
    ],
    "urgency": [
        "You have only thirty minutes left, after that I cannot help you.",
        "Time is running out sir, the system will lock your file very soon.",
    ],
    "extraction": [
        "Complete the verification now, I am waiting on the line.",
        "Finish the formality immediately so that I can close your file.",
        "This is the last warning, sir. Do the needful or the file goes to court.",
        "Every minute you waste makes the penalty bigger, please hurry.",
        "My supervisor is asking why this is pending. Complete it right now.",
        "I am being very patient with you, but my patience is ending.",
    ],
}

# Wording avoids the loop's payment keywords (send/transfer/pay/approve) so the
# offline scammer does not trip the "scammer_stuck" stop on every run.
REVEAL_TEMPLATES = {
    "upi_ids": "Make the deposit to UPI ID {v} and tell me once it is done.",
    "phone_numbers": "If the line drops, call me back on {v} immediately.",
    "urls": "Open this link and follow the steps: {v}",
    "account_numbers": "For manual deposit use this account number {v}, quickly.",
}

IMPATIENT = [
    "Sir, I already explained. Please listen: {last}",
    "Again I am telling you, {last}",
    "Why are you delaying? {last}",
]

STALLS = [
    "Haan ji beta, ek minute, my phone is hanging. Which button should I press first?",
    "Accha accha, I am on the page now but the screen is very small. Where do I type again?",
    "Theek hai beta, I am writing it down on paper. Can you say that slowly once more?",
    "Arrey, my glasses are in the other room. Can you spell it letter by letter please?",
    "Haan ji, I opened the app but it is asking something. What should I tap now?",
    "One minute beta, my grandson usually does this. Which option is it, the green one?",
    "Sorry ji, I pressed the wrong thing and it went back. Can you tell me the details again?",
    "I am very nervous sir, my hands are shaking. Please tell me slowly, what do I enter?",
    "The network is going on and off here, beta. Did you say the number or the ID first?",
    "Accha, I found the page, but it shows a spinning circle. Should I wait or press again?",
    "Haan ji, I am going to the other room where the signal is better. What was the last thing you said?",
    "Theek hai, I will do it, but the text is not opening properly. Can you repeat the link or ID?",
    "Beta, I am old, please be patient. Is it the first box or the second box I fill?",
    "My phone is asking for a password, I do not remember. Is there another way to do it?",
    "Haan ji, battery is low, let me find the charger. Please repeat everything once more?",
    "Accha, now it is loading... it says something is wrong. Which button is the correct one?",
]

LEAK_LINES = [
    "Okay beta, the OTP I got is 482913, is that right?",
    "Haan ji, my card number is 4111111111111111, should I read the rest?",
]


class OfflineSim:
    """One simulated conversation. Seeded, so runs are reproducible."""

    def __init__(self, script: dict, seed: int = 0, leak_prob: float = 0.2):
        self.rng = random.Random(seed)
        self.identity = script.get("claimed_identity", "the department")
        gt = script.get("ground_truth_indicators", {})
        self.reveals = [
            REVEAL_TEMPLATES[f].format(v=v)
            for f in ("upi_ids", "account_numbers", "phone_numbers", "urls")
            for v in gt.get(f, [])
        ]
        self.stalls = STALLS[:]
        self.rng.shuffle(self.stalls)
        self.leak_prob = leak_prob
        self._leaked_at: set[int] = set()
        self._planned: dict[int, bool] = {}
        self._counted: set[int] = set()
        self.simulated_seconds = 0.0
        self._reveal_i = 0
        self._last_reveal = ""

    def _tick(self, key: tuple, lo: float, hi: float):
        # The guardrail may call the persona twice per turn; count time once.
        if key not in self._counted:
            self._counted.add(key)
            self.simulated_seconds += self.rng.uniform(lo, hi)

    def persona(self, history: list[dict], canary: dict) -> str:
        key = len(history)
        if key not in self._planned:
            self._planned[key] = self.rng.random() < self.leak_prob
        self._tick(("p", key), 18, 45)  # a slow, confused typist
        if self._planned[key] and key not in self._leaked_at:
            self._leaked_at.add(key)
            return self.rng.choice(LEAK_LINES)
        turn = sum(1 for h in history if h["role"] == "persona")
        return self.stalls[turn % len(self.stalls)]

    def scammer(self, history: list[dict], script: dict) -> str:
        key = len(history)
        self._tick(("s", key), 8, 25)
        turn = sum(1 for h in history if h["role"] == "scammer")  # opening counts
        stage_names = script.get("stages") or list(STAGE_LINES)
        stage = stage_names[min(turn // 3, len(stage_names) - 1)]
        lines = STAGE_LINES.get(stage, STAGE_LINES["extraction"])
        base = lines[turn % len(lines)]
        parts = [base.format(identity=self.identity)]
        if turn % 2 == 0 and self._reveal_i < len(self.reveals):
            self._last_reveal = self.reveals[self._reveal_i]
            self._reveal_i += 1
            parts.append(self._last_reveal)
        elif self._last_reveal and turn % 3 == 1:
            parts = [self.rng.choice(IMPATIENT).format(last=self._last_reveal)]
        return f"[{turn}] " + " ".join(parts)
