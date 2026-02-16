"""
Routing Types - Data types for probabilistic routing.

Contains enums and dataclasses used across the routing package.

Change Driver: PROBABILISTIC_ROUTING
Changes when: Routing data structures change
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List


# State directory
STATE_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "state"
HISTORY_FILE = STATE_DIR / "routing-history.json"


class RoutingConfidence(Enum):
    """Confidence level for routing decisions."""
    HIGH = "high"          # >90% sure model can handle
    MEDIUM = "medium"      # 70-90% sure
    LOW = "low"            # <70% sure, use higher-tier model


@dataclass
class RoutingDecision:
    """Routing decision with confidence and validation criteria."""
    recommended_model: str
    confidence: RoutingConfidence
    fallback_chain: List[str]
    validation_criteria: List[str]
    reasoning: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "recommended_model": self.recommended_model,
            "confidence": self.confidence.value,
            "fallback_chain": self.fallback_chain,
            "validation_criteria": self.validation_criteria,
            "reasoning": self.reasoning,
        }


@dataclass
class RoutingOutcome:
    """Record of a routing outcome for learning."""
    timestamp: str
    request_hash: str  # Hash of request for privacy
    model: str
    task_type: str
    success: bool
    escalated: bool
    validation_failures: List[str] = field(default_factory=list)
    escalation_path: List[str] = field(default_factory=list)
