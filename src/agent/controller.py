from src.agent.planner import PlannerAgent
from src.agent.executor import ToolExecutor
from src.agent.verifier import VerifierAgent
from src.genai.memory import store_memory
from src.utils.logger import setup_logger

CONFIDENCE_THRESHOLD = 0.75
MAX_RETRIES = 2

logger = setup_logger()

class AgentController:
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ToolExecutor()
        self.verifier = VerifierAgent()

    def run(self, user_query: str) -> dict:
        logger.info(f"Agent started | query='{user_query}'")

        attempt = 0
        last_result = None
        last_verification = None

        while attempt <= MAX_RETRIES:
            logger.info(f"Attempt {attempt + 1} started")

            # STEP 1: Plan
            plan = self.planner.create_plan(user_query)
            logger.info(f"Plan created | steps={len(plan.get('steps', []))}")

            # STEP 2: Execute
            execution_result = self.executor.execute_plan(plan)
            logger.info("Execution completed")

            # STEP 4: Verify
            verification = self.verifier.verify(user_query, execution_result)
            confidence = verification.get("confidence", 0)

            logger.info(
                f"Verification completed | approved={verification.get('approved')} "
                f"| confidence={confidence}"
            )

            last_result = execution_result
            last_verification = verification

            if verification.get("approved") and confidence >= CONFIDENCE_THRESHOLD:
                logger.info("Result approved, storing memory")

                memory_text = f"""
Goal: {execution_result.get('goal')}
Results: {execution_result.get('results')}
"""
                store_memory(memory_text)

                logger.info("Agent finished successfully")

                return {
                    "status": "success",
                    "attempts": attempt + 1,
                    "execution": execution_result,
                    "verification": verification
                }

            logger.warning("Low confidence detected, retrying")
            attempt += 1

        logger.error("Agent failed after max retries")

        return {
            "status": "failed",
            "attempts": attempt,
            "execution": last_result,
            "verification": last_verification,
            "message": "Low confidence after retries. Manual review recommended."
        }
