# generation/agents/faq_generator.py
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from generation.utils.llm_manager import get_llm

class FAQItem(BaseModel):
    question: str = Field(description="سوال متداول و کاربردی کاربر")
    answer: str = Field(description="پاسخ کوتاه، دقیق و اقناع‌کننده (حداکثر ۲ یا ۳ جمله)")

class FAQList(BaseModel):
    faqs: List[FAQItem]

FAQ_PROMPT = """شما متخصص بخش پرسش و پاسخ (FAQ) سایت‌های خدماتی هستید.
با توجه به مشخصات زیر و محتوای تولید شده، ۳ الی ۵ سوال متداول و بسیار مهم که کاربران در گوگل سرچ می‌کنند را به همراه پاسخ‌های تخصصی تولید کنید.

مشخصات هدف:
- کلمه کلیدی اصلی: {keyword}
- کانتکست موجودیت (برند/مدل): {rich_entity_context}

محتوای مقاله:
---
{compiled_body}
---

قوانین:
سوالات را دقیقاً متناسب با کانتکست موجودیت بپرسید. پاسخ‌ها نباید عمومی باشند؛ از اطلاعات موجود در متن مقاله برای پاسخگویی استفاده کنید.
فقط خروجی را به فرمت JSON ساختاریافته برگردانید.
"""

def generate_faqs(keyword: str, compiled_body: str, rich_entity_context: str = "عمومی") -> list:
    try:
        # برای FAQ از مدل فلش استفاده می‌کنیم چون دیتای اصلی از متن استخراج می‌شود و نیاز به استدلال سنگین ندارد
        llm = get_llm(temperature=0.3)
        structured_llm = llm.with_structured_output(FAQList)
        prompt = ChatPromptTemplate.from_template(FAQ_PROMPT)
        chain = prompt | structured_llm
        
        result = chain.invoke({
            "keyword": keyword, 
            "rich_entity_context": rich_entity_context,
            "compiled_body": compiled_body
        })
        return [faq.model_dump() for faq in result.faqs]
    except Exception as e:
        print(f"[-] FAQ Generator Error: {e}")
        return []