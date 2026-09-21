import logging
import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from schemas import RiskReportSchema
from prompts import generate_risk_report_prompt
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

# The Intelligence Service
async def generate_risk_report(discrepancy_details: List[Dict[str, Any]], bl_data: Dict[str, Any]) -> dict:
    """
    Analyzes document discrepancies against maritime law (SOLAS VGM), trade finance (UCP 600),
    and local Malaysian jurisdiction rules.
    """
    try:
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMENI_INTELLIGENCE_MODEL"),
            temperature=0.3,
            max_retries=2
        )

        structured_llm = llm.with_structured_output(RiskReportSchema)

        system_prompt = generate_risk_report_prompt

        # Format the context for the LLM
        prompt_context = f"Bill of Lading Extracted Data:\n{bl_data}\n\nDetected SI vs BL Discrepancies:\n"

        if not discrepancy_details:
            prompt_context += "None. Documents match perfectly."
        else:
            for d in discrepancy_details:
                prompt_context += f"- Field '{d['field']}' changed from SI ({d['si_value']}) to BL ({d['bl_value']}). Delta: {d['delta']}\n"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt_context)
        ]

        # Invoke Gemini
        result: RiskReportSchema = await structured_llm.ainvoke(messages)
        return result.model_dump()

    except Exception as e:
        logger.error(f"Intelligence Layer failed: {e}")
        return {
            "overall_risk_level": "UNKNOWN",
            "compliance_flags": ["System Analysis Failed"],
            "financial_and_safety_impact": "Could not generate automated risk report due to a system error.",
            "recommended_action": "Manual compliance and safety review required."
        }