import logging
from typing import Optional
from pydantic import BaseModel, Field
from schemas import ShipmentExtractionSchema
from prompts import extractor_llm_prompt
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import GoogleAPIError
from dotenv import load_dotenv

from vision_ocr import transcribe_scanned_pdf
from file_ingestion import ingest_document

load_dotenv()



# Async Extraction Service (Direct Invocation)
async def extract_shipment_data(document_text: str) -> dict:
    """
    Extracts the 7 required fields from document text using Gemini 1.5 Flash.
    Uses explicit message passing rather than LangChain pipes.

    Returns:
        dict: {"data": dict or None, "error": str or None}
    """
    if not document_text or not document_text.strip():
        return {"data": None, "error": "Empty document text provided."}

    try:
        # Initialize the model
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMENI_EXTRACTION_MODEL"),
            temperature=0.0,
            max_retries=2
        )

        # Bind the Pydantic schema directly to the model
        structured_llm = llm.with_structured_output(ShipmentExtractionSchema)

        # Construct the explicit message array
        messages = [
            SystemMessage(content=extractor_llm_prompt),
            HumanMessage(content=f"Document Text:\n\n{document_text}")
        ]

        # Invoke the structured model directly with the message array
        result: ShipmentExtractionSchema = await structured_llm.ainvoke(messages)

        return {"data": result.model_dump(), "error": None}

    except GoogleAPIError as api_err:
        logging.error(f"API Error during extraction: {api_err}")
        return {"data": None, "error": f"API Error: {str(api_err)}"}
    except Exception as e:
        logging.error(f"Unexpected extraction error: {e}")
        return {"data": None, "error": f"Extraction failed: {str(e)}"}

