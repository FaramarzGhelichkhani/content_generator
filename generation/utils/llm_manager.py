# generation/utils/llm_manager.py
from seoengine.settings import GEMINI_API_KEY
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold

def get_llm(model_name="gemini-3.5-flash-lite", temperature=0.3):
    """
    برگرداندن یک اینستنس تنظیم شده از مدل زبانی.
    """
    api_key = GEMINI_API_KEY
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        # جلوگیری از گیر دادن جمینای به مسائل ایمنی سخت‌گیرانه (اختیاری)
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )
    return llm
