#!/usr/bin/env python3
"""
Overnight Execution Runner - CLI wrapper for OvernightWorkExecutor.

Invoked by systemd timer at 22:00 to execute queued overnight work.

Usage:
    python3 overnight_execution_runner.py \
        --queue-file ~/.claude/.../temporal-work-queue.json \
        --results-dir ~/.claude/.../overnight-results \
        --max-concurrent 3 \
        --timeout 10800

Change Driver: OVERNIGHT_EXECUTION
Changes when: Execution strategy or CLI interface changes
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add implementation directory to path
IMPL_DIR = Path(__file__).parent
sys.path.insert(0, str(IMPL_DIR))

from temporal_scheduler import (
    TemporalScheduler,
    OvernightWorkExecutor,
    TimedWorkItem,
    WorkTiming,
    QUEUE_FILE,
    STATE_DIR,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_scheduled_work(queue_file: Path) -> List[TimedWorkItem]:
    """
    Load scheduled work items from queue file.

    Args:
        queue_file: Path to temporal-work-queue.json

    Returns:
        List of TimedWorkItem scheduled for overnight execution
    """
    if not queue_file.exists():
        logger.info(f"No queue file found at {queue_file}")
        return []

    try:
        with open(queue_file, 'r') as f:
            data = json.load(f)

        scheduled_work = data.get("scheduled_async", [])

        if not scheduled_work:
            logger.info("No work scheduled for tonight")
            return []

        # Convert to TimedWorkItem objects
        work_items = [TimedWorkItem.from_dict(item) for item in scheduled_work]

        logger.info(f"Loaded {len(work_items)} work items for overnight execution")
        return work_items

    except Exception as e:
        logger.error(f"Error loading queue file: {e}")
        return []


def create_agent_executor(project_contexts: Dict[str, str]) -> callable:
    """
    Create agent executor function that spawns Claude agents.

    This function needs to:
    1. Spawn Claude agent in correct project directory
    2. Pass work description as prompt
    3. Capture and return result

    Args:
        project_contexts: Map of work_id to project_path

    Returns:
        Callable(work_item, model) that executes agent and returns result
    """
    # Find claude executable
    claude_path = None
    for path in [os.path.expanduser('~/.local/bin/claude'), '/usr/local/bin/claude', '/usr/bin/claude']:
        if os.path.exists(path):
            claude_path = path
            break

    if not claude_path:
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                claude_path = result.stdout.strip()
        except Exception:
            pass

    if not claude_path:
        logger.warning("Claude CLI not found in PATH. Falling back to simulated execution.")

    def executor(work_item: Any, model: str) -> str:
        """
        Execute work by spawning Claude agent.

        Args:
            work_item: TimedWorkItem with description and project context
            model: Model tier (sonnet, haiku, opus)

        Returns:
            Result string from agent execution
        """
        # Get project path from work item
        project_path = project_contexts.get(work_item.id, os.getcwd())
        work_description = work_item.description

        if not claude_path:
            # Fallback to simulation if Claude CLI not available
            logger.info(f"SIMULATED EXECUTION: {work_description[:100]}")
            logger.info(f"  Model: {model}")
            import time
            time.sleep(2)
            return f"Simulated result for: {work_description[:50]}"

        logger.info(f"Executing via Claude CLI: {work_description[:100]}")
        logger.info(f"  Model: {model}")
        logger.info(f"  Project: {project_path}")

        try:
            # Spawn Claude agent with --print mode for non-interactive execution
            process = subprocess.run(
                [claude_path, '--print', '--model', model, work_description],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour per task
            )

            if process.returncode != 0:
                error_msg = f"Claude agent failed (exit code {process.returncode})"
                if process.stderr:
                    error_msg += f": {process.stderr[:500]}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            result = process.stdout.strip()
            logger.info(f"  Completed: {len(result)} chars output")
            return result

        except subprocess.TimeoutExpired:
            logger.error(f"  Timeout after 1 hour")
            raise RuntimeError("Agent execution timeout after 1 hour")
        except Exception as e:
            logger.error(f"  Agent execution failed: {e}")
            raise

    return executor


async def execute_overnight_work(
    queue_file: Path,
    results_dir: Path,
    max_concurrent: int = 3,
    timeout: int = 10800  # 3 hours
) -> Dict[str, Any]:
    """
    Main execution function for overnight work.

    Args:
        queue_file: Path to queue file
        results_dir: Directory for results
        max_concurrent: Max concurrent tasks
        timeout: Overall timeout in seconds

    Returns:
        Dict of results
    """
    logger.info("=== Overnight Work Execution Started ===")
    logger.info(f"Queue file: {queue_file}")
    logger.info(f"Results directory: {results_dir}")
    logger.info(f"Max concurrent: {max_concurrent}")
    logger.info(f"Timeout: {timeout}s ({timeout/3600:.1f}h)")

    # Load scheduled work
    work_items = load_scheduled_work(queue_file)

    if not work_items:
        logger.info("No work to execute. Exiting.")
        return {}

    # Extract project contexts from work items
    project_contexts = {}
    for item in work_items:
        # Use project_path from work item, fallback to current directory
        project_contexts[item.id] = item.project_path or os.getcwd()
        logger.info(f"Work item {item.id}: project={item.project_name or 'unknown'} path={project_contexts[item.id]}")

    # Create scheduler and executor
    scheduler = TemporalScheduler(state_file=queue_file)
    executor = OvernightWorkExecutor(scheduler)

    # Create agent executor function
    agent_executor = create_agent_executor(project_contexts)

    # Execute with timeout
    try:
        results = await asyncio.wait_for(
            executor.execute_overnight_queue(work_items, agent_executor),
            timeout=timeout
        )

        logger.info(f"=== Overnight Work Completed: {len(results)} items ===")
        return results

    except asyncio.TimeoutError:
        logger.error(f"Overnight execution timed out after {timeout}s")
        return {"error": "Execution timeout"}
    except Exception as e:
        logger.error(f"Overnight execution failed: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Execute scheduled overnight work"
    )

    parser.add_argument(
        '--queue-file',
        type=Path,
        default=QUEUE_FILE,
        help='Path to temporal work queue file'
    )

    parser.add_argument(
        '--results-dir',
        type=Path,
        default=STATE_DIR / "overnight-results",
        help='Directory for result files'
    )

    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=3,
        help='Maximum concurrent tasks'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=10800,  # 3 hours
        help='Overall timeout in seconds'
    )

    parser.add_argument(
        '--log-file',
        type=Path,
        help='Path to log file (optional)'
    )

    args = parser.parse_args()

    # Setup additional file logging if specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(
            logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        )
        logger.addHandler(file_handler)

    # Ensure results directory exists
    args.results_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Execute overnight work
    try:
        results = asyncio.run(
            execute_overnight_work(
                queue_file=args.queue_file,
                results_dir=args.results_dir,
                max_concurrent=args.max_concurrent,
                timeout=args.timeout
            )
        )

        # Exit code based on results
        if not results:
            sys.exit(0)  # No work, success
        elif "error" in results:
            sys.exit(1)  # Error occurred
        else:
            # Check for any failed items
            failures = [k for k, v in results.items() if "error" in v]
            if failures:
                logger.warning(f"Some items failed: {len(failures)}/{len(results)}")
                sys.exit(2)  # Partial success
            else:
                sys.exit(0)  # Full success

    except KeyboardInterrupt:
        logger.info("Overnight execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
