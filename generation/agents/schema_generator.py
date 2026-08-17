# generation/agents/schema_generator.py
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from generation.utils.llm_manager import get_llm

class SchemaOutput(BaseModel):
    schema_json_string: str = Field(description="کد کامل و معتبر JSON-LD اسکیما (شامل ترکیبی از Article و FAQPage یا LocalBusiness در صورت نیاز) بدون هیچگونه تگ markdown")

SCHEMA_PROMPT = """شما یک متخصص تکنیکال سئو هستید. وظیفه شما تولید ساختار کدهای اسکیما (Schema JSON-LD) برای صفحه زیر است.

مشخصات صفحه:
- کلمه کلیدی: {keyword}
- آدرس صفحه: {url}
- تیتر اصلی: {h1}
- متا دیسکریپشن: {meta}

لیست سوالات متداول صفحه (برای افزودن به اسکیمای FAQPage):
{faqs}

یک کد غنی، استاندارد و کاملاً معتبر JSON-LD بدون ساختارهای markdown (بدندون عیارت ```json) تولید کنید.
"""

def generate_page_schema(keyword: str, url: str, h1: str, meta: str, faqs: list) -> dict:
    try:
        llm = get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(SchemaOutput)
        prompt = ChatPromptTemplate.from_template(SCHEMA_PROMPT)
        chain = prompt | structured_llm
        
        result = chain.invoke({
            "keyword": keyword, "url": url, "h1": h1, "meta": meta, "faqs": str(faqs)
        })
        import json
        return json.loads(result.schema_json_string)
    except Exception as e:
        print(f"[-] Schema Generator Error: {e}")
        return {}