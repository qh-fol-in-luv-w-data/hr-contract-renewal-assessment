# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""Centralized AI prompt constants for the cnb_2as application.

Organized by domain:
- eval_prompts:   Evaluation pipeline agents (ROLE, COMPETENCY, EVIDENCE, etc.)
- scan_prompts:   Phiếu thử việc scan prompts (VISION, KPI, HOI_NHAP, etc.)
- review_prompts: Thu-viec AI review pipeline (_SYSTEM_PROMPT, _CHAT_SYSTEM)
"""

from cnb_2as.services.prompts.eval_prompts import (
    COMPETENCY_GENERATOR_SYSTEM,
    EVIDENCE_EXTRACTOR_SYSTEM,
    RECOMMENDATION_AGENT_SYSTEM,
    ROLE_ANALYZER_SYSTEM,
    SCORING_AGENT_SYSTEM,
    _DAILY_REPORT_SYSTEM,
    _MANAGER_PROPOSAL_SYSTEM,
)
from cnb_2as.services.prompts.scan_prompts import (
    _ANALYZE_PROMPT,
    _EXTRACT_PROMPT,
    _MERGE_PROMPT,
    HOI_NHAP_PROMPT,
    KPI_PROMPT,
    SAN_PHAM_PROMPT,
    VISION_JSON_PROMPT,
)
from cnb_2as.services.prompts.review_prompts import (
    _CHAT_SYSTEM,
    _SYSTEM_PROMPT,
)

__all__ = [
    # eval
    "COMPETENCY_GENERATOR_SYSTEM", "EVIDENCE_EXTRACTOR_SYSTEM",
    "RECOMMENDATION_AGENT_SYSTEM", "ROLE_ANALYZER_SYSTEM",
    "SCORING_AGENT_SYSTEM", "_DAILY_REPORT_SYSTEM", "_MANAGER_PROPOSAL_SYSTEM",
    # scan
    "_ANALYZE_PROMPT", "_EXTRACT_PROMPT", "_MERGE_PROMPT",
    "HOI_NHAP_PROMPT", "KPI_PROMPT", "SAN_PHAM_PROMPT", "VISION_JSON_PROMPT",
    # review
    "_CHAT_SYSTEM", "_SYSTEM_PROMPT",
]
