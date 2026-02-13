#!/usr/bin/env python3
"""
Request Orchestration Script - Deterministic Agent Routing

Receives user request, consults routing system, spawns appropriate
agent, monitors execution, handles escalation.

Usage:
    orchestrate-request.py "User's request here"
    orchestrate-request.py --interactive  # Read from stdin
    orchestrate-request.py --session SESSION_ID "Request"

Change Driver: ORCHESTRATION_LOGIC
Changes when: Orchestration strategy or agent coordination patterns change
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class RequestOrchestrator:
    """Orchestrates user requests through routing and agent execution."""

    def __init__(
        self,
        project_root: Path,
        session_id: Optional[str] = None,
        interactive: bool = False
    ):
        self.project_root = project_root
        self.session_id = session_id or self._generate_session_id()
        self.interactive = interactive

        # Paths
        self.router_dir = project_root / "plugins/infolead-claude-subscription-router"
        self.routing_script = self.router_dir / "implementation/routing_core.py"
        self.metrics_dir = Path.home() / ".claude/infolead-claude-subscription-router/metrics"
        self.state_dir = Path.home() / ".claude/infolead-claude-subscription-router/state"

        # Ensure directories exist
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Find claude executable
        self.claude_path = self._find_claude_cli()

    def _find_claude_cli(self) -> Optional[str]:
        """Find claude executable in PATH."""
        try:
            result = subprocess.run(
                ['which', 'claude'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def get_routing_decision(self, request: str) -> Dict:
        """
        Call routing_core.py to get routing decision.

        Returns:
            Dict with 'decision', 'agent', 'reason', 'confidence'
        """
        if not self.routing_script.exists():
            logger.error(f"Routing script not found: {self.routing_script}")
            return self._fallback_routing()

        try:
            result = subprocess.run(
                ['python3', str(self.routing_script), '--json'],
                input=request,
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, 'CLAUDE_NO_HOOKS': '1'}
            )

            if result.returncode != 0:
                logger.warning(f"Routing failed: {result.stderr}")
                return self._fallback_routing()

            return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Routing error: {e}")
            return self._fallback_routing()

    def _fallback_routing(self) -> Dict:
        """Fallback routing decision when routing_core fails."""
        return {
            "decision": "direct",
            "agent": "sonnet-general",
            "reason": "Routing system unavailable, defaulting to sonnet",
            "confidence": 0.5
        }

    def execute_agent(
        self,
        agent: str,
        request: str,
        timeout: int = 3600
    ) -> Tuple[str, int]:
        """
        Spawn Claude agent and execute request.

        Returns:
            Tuple of (output, exit_code)
        """
        if not self.claude_path:
            logger.error("Claude CLI not found in PATH")
            return "ERROR: Claude CLI not available", 1

        # Determine model from agent name
        model = self._agent_to_model(agent)

        # Construct prompt with output requirements
        prompt = f"""{request}

REQUIRED OUTPUT: You must return usable results:
- Direct results in your response, OR
- File path to where results are stored, OR
- Summary of actions (files modified, counts, specifics)

Do NOT complete silently."""

        logger.info(f"Executing agent: {agent} (model: {model})")

        try:
            # Spawn Claude agent
            process = subprocess.run(
                [
                    self.claude_path,
                    '--print',  # Non-interactive mode
                    '--model', model,
                    prompt
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'CLAUDE_NO_HOOKS': '1'}
            )

            return process.stdout, process.returncode

        except subprocess.TimeoutExpired:
            logger.error(f"Agent timeout after {timeout}s")
            return f"ERROR: Agent execution timeout after {timeout}s", 124
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return f"ERROR: {e}", 1

    def _agent_to_model(self, agent: str) -> str:
        """Map agent name to model tier."""
        if 'haiku' in agent.lower():
            return 'haiku'
        elif 'opus' in agent.lower():
            return 'opus'
        else:
            return 'sonnet'

    def check_escalation_needed(self, output: str) -> Optional[str]:
        """
        Check if agent output indicates escalation needed.

        Returns:
            Agent name to escalate to, or None
        """
        # Look for escalation signals in output
        escalation_markers = [
            "escalating to",
            "routing to",
            "needs opus",
            "requires higher capability"
        ]

        output_lower = output.lower()
        for marker in escalation_markers:
            if marker in output_lower:
                # Parse which agent to escalate to
                if "opus" in output_lower:
                    return "opus-general"
                elif "sonnet" in output_lower:
                    return "sonnet-general"

        return None

    def record_metrics(
        self,
        request: str,
        routing_decision: Dict,
        execution_result: Dict
    ):
        """Record execution metrics."""
        from datetime import datetime
        import hashlib

        timestamp = datetime.now().isoformat()
        request_hash = hashlib.sha256(request.encode()).hexdigest()[:16]
        today = datetime.now().strftime("%Y-%m-%d")

        metrics_entry = {
            "record_type": "orchestrated_execution",
            "timestamp": timestamp,
            "session_id": self.session_id,
            "request_hash": request_hash,
            "routing_decision": routing_decision,
            "execution_result": execution_result,
            "orchestration_mode": "external"
        }

        metrics_file = self.metrics_dir / f"{today}.jsonl"

        try:
            with open(metrics_file, 'a') as f:
                f.write(json.dumps(metrics_entry) + '\n')
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")

    def orchestrate(self, request: str) -> str:
        """
        Main orchestration logic.

        1. Get routing decision
        2. Execute agent
        3. Check for escalation
        4. Record metrics
        5. Return result
        """
        logger.info(f"Orchestrating request (session: {self.session_id})")

        # Step 1: Routing decision
        routing = self.get_routing_decision(request)
        logger.info(f"Routing: {routing['decision']} → {routing.get('agent', 'router')} ({routing.get('confidence', 0):.2f})")
        logger.info(f"Reason: {routing['reason']}")

        # Determine agent to execute
        if routing['decision'] == 'escalate':
            agent = 'router'  # Escalate to router agent
        else:
            agent = routing.get('agent', 'sonnet-general')

        # Step 2: Execute agent
        output, exit_code = self.execute_agent(agent, request)

        # Step 3: Check for escalation
        escalation_agent = self.check_escalation_needed(output)
        if escalation_agent and exit_code == 0:
            logger.info(f"Agent requested escalation to: {escalation_agent}")
            output, exit_code = self.execute_agent(escalation_agent, request)

        # Step 4: Record metrics
        execution_result = {
            "agent": agent,
            "exit_code": exit_code,
            "escalated": escalation_agent is not None,
            "final_agent": escalation_agent or agent
        }
        self.record_metrics(request, routing, execution_result)

        # Step 5: Return result
        if exit_code != 0:
            logger.error(f"Execution failed (exit {exit_code})")

        return output


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Orchestrate user requests through deterministic routing"
    )

    parser.add_argument(
        'request',
        nargs='?',
        help='User request to execute'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Read request from stdin'
    )

    parser.add_argument(
        '--session',
        help='Session ID for state tracking'
    )

    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path.cwd(),
        help='Project root directory'
    )

    args = parser.parse_args()

    # Get request
    if args.interactive:
        request = sys.stdin.read().strip()
    elif args.request:
        request = args.request
    else:
        parser.error("Provide request as argument or use --interactive")

    # Create orchestrator
    orchestrator = RequestOrchestrator(
        project_root=args.project_root,
        session_id=args.session,
        interactive=args.interactive
    )

    # Orchestrate request
    result = orchestrator.orchestrate(request)

    # Output result
    print(result)


if __name__ == "__main__":
    main()
