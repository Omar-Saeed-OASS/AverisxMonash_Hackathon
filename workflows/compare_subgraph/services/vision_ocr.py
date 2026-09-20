import base64
import os
import pymupdf
import logging
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded
from dotenv import load_dotenv
load_dotenv()

async def transcribe_scanned_pdf(file_bytes: bytes) -> dict:
    """
    Takes raw bytes of a scanned PDF, converts pages to images,
    and uses MLLM to transcribe them into Markdown.

    Returns:
        dict: {"content": str, "error": str or None}
    """

    try:
        # Attempt to parse the byte stream
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as pdf_err:
            return {"content": "", "error": f"Corrupted PDF byte stream: {str(pdf_err)}"}

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMENI_OCR_MODEL"),
            temperature=0.0,
            max_retries=2
        )

        markdown_pages = []

        for page_num, page in enumerate(doc):
            zoom_matrix = pymupdf.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)

            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            prompt_content = [
                {
                    "type": "text",
                    "text": (
                        "You are a strict document transcription engine. "
                        "Convert the text and tables in this image into clean Markdown. "
                        "Preserve all structural layouts, column headers, and data grids exactly. "
                        "Do not add conversational filler."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                }
            ]

            message = HumanMessage(content=prompt_content)

            # API Call with exception handling
            try:
                response = await llm.ainvoke([message])
                markdown_pages.append(f"### Page {page_num + 1}\n\n{response.content[0].get("text", "")}\n")
            except (ResourceExhausted, DeadlineExceeded) as network_err:
                doc.close()
                return {"content": "", "error": f"API Quota/Timeout: {str(network_err)}"}
            except Exception as model_err:
                doc.close()
                return {"content": "", "error": f"Model inference failed: {str(model_err)}"}

        doc.close()

        return {"content": "\n".join(markdown_pages), "error": None}

    except Exception as fatal_err:
        logging.error(f"Fatal error in vision transcription: {fatal_err}")
        return {"content": "", "error": f"Unexpected fatal error: {str(fatal_err)}"}

