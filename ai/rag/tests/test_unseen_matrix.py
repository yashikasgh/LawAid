import unittest
from ai.rag.pipeline import sanitize_and_validate_legal_chat_reply

class TestUnseenIncidentMatrix(unittest.TestCase):
    """
    Generalized test matrix testing novel/paraphrased incidents against
    grounding rules, statutory element overrides, relevance filters, and prose consistency.
    """

    def test_unseen_matrix_prose_normalization(self):
        # 1. Theft described without the word theft
        raw_reply_1 = (
            "### 2. Applicable sections\n"
            "- **BNS Section 303 (Theft)** — Established\n"
            "### 6. Bottom line summary\n"
            "Section 303 applies."
        )
        ctx_1 = [{"section": "Section 303", "overall_applicability": "established"}]
        res_1 = sanitize_and_validate_legal_chat_reply(raw_reply_1, ctx_1)
        self.assertIn("Section 303", res_1)
        self.assertIn("Established", res_1)

        # 2. Attack with theft - Section 134 conditional contradiction
        raw_reply_2 = (
            "### 2. Applicable sections\n"
            "- **Section 134 (Assault during theft)** — Facts establish this provision\n"
            "### 6. Bottom line summary\n"
            "The most likely legal sections are Section 303 and Section 134."
        )
        ctx_2 = [
            {"section": "Section 303", "overall_applicability": "potentially_applicable"},
            {"section": "Section 134", "overall_applicability": "potentially_applicable"}
        ]
        res_2 = sanitize_and_validate_legal_chat_reply(raw_reply_2, ctx_2)
        self.assertNotIn("Section 134 (Assault during theft)** — Facts establish", res_2)
        self.assertIn("Potentially Applicable", res_2)
        self.assertNotIn("The most likely legal sections are Section 303 and Section 134.", res_2)

        # 3. Section 130 statutory element override
        raw_reply_3 = (
            "### 2. Applicable sections\n"
            "- **Section 130 (Assault)** — Section 130 applies because of the attack."
        )
        ctx_3 = [{"section": "Section 130", "overall_applicability": "potentially_applicable"}]
        res_3 = sanitize_and_validate_legal_chat_reply(raw_reply_3, ctx_3)
        self.assertIn("gestures or preparation", res_3)

        # 4. Mandatory punishment transformation safeguard
        raw_reply_4 = "Under Section 309, the punishment is 10 years."
        ctx_4 = [{"section": "Section 309", "overall_applicability": "potentially_applicable"}]
        res_4 = sanitize_and_validate_legal_chat_reply(raw_reply_4, ctx_4)
        self.assertIn("imprisonment up to 10 years", res_4)
        self.assertNotIn("the punishment is 10 years", res_4)

        # 5. Unauthorized house entry - Section 329 conditional consistency
        raw_reply_5 = (
            "### 2. Applicable sections\n"
            "- **Section 329 (House-trespass)** — Facts establish this provision\n"
            "### 6. Bottom line summary\n"
            "Section 329 clearly applies as a definite charge."
        )
        ctx_5 = [{"section": "Section 329", "overall_applicability": "potentially_applicable"}]
        res_5 = sanitize_and_validate_legal_chat_reply(raw_reply_5, ctx_5)
        self.assertIn("Potentially Applicable", res_5)

if __name__ == "__main__":
    unittest.main()
