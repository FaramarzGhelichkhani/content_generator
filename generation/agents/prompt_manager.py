# generation/agents/prompt_manager.py
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from taxonomy.models import TaxonomyNode
from content.models import InternalLink, PageBrief, PageContent

# =========================================================
# دیتابیس بومی کلمات کلیدی تخصصی برای لینک‌های خارجی سئو
# =========================================================
EXTERNAL_LINKS_MAP = {
    "ایموبلایزر": "https://fa.wikipedia.org/wiki/%D8%A7%DB%8C%D9%85%D9%88%D8%A8%D9%84%D8%A7%DB%8C%D8%B2%D8%B1",
    "Immobilizer": "https://fa.wikipedia.org/wiki/%D8%A7%DB%8C%D9%85%D9%88%D8%A8%D9%84%D8%A7%DB%8C%D8%B2%D8%B1",
    "دیاگ": "https://fa.wikipedia.org/wiki/%D8%AF%DB%8C%D8%A7%DA%AF",
    "برد الکترونیکی" : "https://fa.wikipedia.org/wiki/%D8%A8%D8%B1%D8%AF_%D9%85%D8%AF%D8%A7%D8%B1_%DA%86%D8%A7%D9%BE%DB%8C",
}

# =========================================================
# ۱. تعریف ساختارهای خروجی با Pydantic (Schema)
# =========================================================

# --- اسکیماهای Planner ---
class ContentBlock(BaseModel):
    block_type: str = Field(description="نوع بلوک (مانند: hero, introduction, main_section, image, comparison, step_by_step, table, faq, cta, related_content, conclusion, specs)")
    title: str = Field(description="عنوان بلوک (H2/H3). اگر نوع بلوک image است، این فیلد باید شامل یک جمله کوتاه برای ویژگی Alt تصویر باشد.")
    purpose_and_intent: str = Field(description="هدف این بلوک چیست و رایتر دقیقا باید درباره چه چیزی بنویسد؟")
    block_word_count: int = Field(description="بودجه تعداد کلمات تخصیص یافته به این بلوک")
    target_keywords: List[str] = Field(description="کلمات کلیدی هدف و LSI هایی که باید در این بلوک استفاده شوند")
    internal_links_to_include: List[str] = Field(description="لیست انکرتکست‌ها و لینک‌هایی که رایتر باید در این بلوک جایگذاری کند (در صورت وجود)", default_factory=list)

class PageOutline(BaseModel):
    seo_title: str = Field(description="عنوان سئو (Title Tag). حرفه‌ای، اگزکت و بدون کلمات اضافه. الزامی به استفاده خشک از ترکیب 'برند+مدل' نیست؛ نحوه سرچ طبیعی کاربر را لحاظ کنید.")
    meta_description: str = Field(description="متا دیسکریپشن (حداکثر 150 کاراکتر)")
    h1_title: str = Field(description="عنوان اصلی صفحه (H1). دقیقاً بر اساس کلمه کلیدی اصلی و رفتار جستجوی کاربر باشد.")
    focus_keyword: str = Field(description="کلمه کلیدی که براساس کلمه کلید اصلی و موجودیت هدف باید بسازی بعدا جهت بررسی سئواستفاده خواهد شد.")
    blocks: List[ContentBlock] = Field(description="لیست بلوک‌های محتوایی به ترتیب منطقی")

# --- اسکیمای Writer ---
class WriterOutput(BaseModel):
    content: str = Field(description="محتوای نهایی تولید شده برای بلوک (رشته HTML، یا JSON برای faq/specs، یا متن ساده برای image بر اساس قوانین)")

# --- اسکیماهای SEO Reviewer ---
class BlockFeedback(BaseModel):
    block_id: int = Field(description="شناسه یا همان block_id بلوکی که ایراد دارد")
    feedback: str = Field(description="دلیل دقیق رد شدن بلوک و راهنمایی کاملاً شفاف فنی به ایجنت نویسنده برای اصلاح آن")

class SEOAuditResult(BaseModel):
    score: int = Field(description="نمره کل سئوی معنایی و ساختاری صفحه از 0 تا 100")
    is_approved: bool = Field(description="آیا سئوی صفحه مورد تایید است؟")
    failed_blocks: List[BlockFeedback] = Field(description="لیست بلوک‌هایی که استانداردهای سئو را پاس نکرده‌اند")
    missing_entities: List[str] = Field(description="موجودیت‌های کلیدی LSI که در متن غایب هستند")
    summary_report: str = Field(description="گزارش نهایی و تحلیل کلی از وضعیت سئوی معنایی صفحه")

# --- اسکیمای Humanizer (بازنویس) ---
class HumanizedBlock(BaseModel):
    block_id: int = Field(description="شناسه (block_id) بلوک ورودی")
    humanized_content: str = Field(description="محتوای بازنویسی شده و روان برای این بلوک")

class HumanizerOutput(BaseModel):
    blocks: List[HumanizedBlock] = Field(description="لیست تمام بلوک‌های بازنویسی شده")

# --- اسکیمای Link Builder ---
class LinkBuilderOutput(BaseModel):
    linked_html: str = Field(description="کد HTML نهایی مقاله که دقیقاً مشابه متن ورودی است، با این تفاوت که لینک‌های داخلی و خارجی در آن جایگذاری شده‌اند.")

# =========================================================
# ۲. کلاس مدیریت پرامپت‌ها
# =========================================================
class PromptManager:
    def __init__(self, page_brief: PageBrief):
        self.brief = page_brief
        self.project = page_brief.project

    # ---------------------------------------------------------
    # متدهای تولید کانتکست (Context Generators)
    # ---------------------------------------------------------
    def _get_intent_and_service_context(self):
        keyword = self.brief.keyword
        intent_desc = keyword.intent.description if keyword.intent else ""
        service_name = self.brief.service_type.name if self.brief.service_type else "عمومی/آموزشی"
        service_desc = self.brief.service_type.description if self.brief.service_type else ""
        
        page_scope = "پیلار اصلی خدمات (مرجع کامل)"
        if self.brief.location:
            page_scope = f"کلاستر محلی (ویژه شهر/منطقه {self.brief.location.name})"
        elif self.brief.page_level == 2:
            page_scope = "پیلار جامع برند"
        elif self.brief.page_level == 3:
            page_scope = "پیلار تخصصی مدل"
        elif self.brief.page_level == 4:
            page_scope = "کلاستر تخصصی/فرعی مدل"

        context = f"""
[مشخصات کلی صفحه]
- سرویس اصلی: {service_name}
- گستره و نوع صفحه: {page_scope}

[هدف و نیت کاربر (Search Intent)]
{intent_desc}

[شرح خدمات/محصول این صفحه]
{service_desc}

[کلمه کلیدی اصلی (Focus Keyword)]
{keyword.text}

[کلمات کلیدی کمکی و لانگ‌تیل‌ها (LSI & Extra Keywords)]
{keyword.extra_keywords_text}
"""
        if self.brief.location:
            context += f"""
[دستورالعمل ویژه سئوی محلی (Local SEO)]
این محتوا منحصراً برای شهر/محله '{self.brief.location.name}' است.
قوانین محلی: حتماً بلوک‌هایی برای تاکید بر "سرعت اعزام نیروی سیار در {self.brief.location.name}"، "پوشش‌دهی مناطق اطراف" و "خدمات در محل" در نظر بگیرید. به هیچ وجه به شهرها یا مناطق نامرتبط اشاره نکنید.
"""
        return context

    def _get_taxonomy_context(self):
        taxonomy_context = ""
        if self.brief.page_level == 1 and not self.brief.entity and not self.brief.location:
            brands = TaxonomyNode.objects.filter(project=self.project, kind=TaxonomyNode.Kind.BRAND, parent=None, is_active=True)
            catalog = [f"- {brand.name} (مدل‌ها: {', '.join(brand.children.filter(kind=TaxonomyNode.Kind.MODEL, is_active=True).values_list('name', flat=True))})" for brand in brands]
            taxonomy_context = "[دستورالعمل جامعیت صفحه اصلی]: شما باید در یک یا چند بلوک صراحتاً ذکر کنید که این سرویس برای تمام برندها و مدل‌های زیر ارائه می‌شود:\n" + "\n".join(catalog)
            
        elif self.brief.page_level == 2 and self.brief.entity and self.brief.entity.kind == TaxonomyNode.Kind.BRAND:
            models_str = ", ".join(self.brief.entity.children.filter(kind=TaxonomyNode.Kind.MODEL, is_active=True).values_list('name', flat=True))
            taxonomy_context = f"[موجودیت هدف]: نام برند: {self.brief.entity.name}\n[دستورالعمل برند]: باید حتما بلوکی طراحی کنید که در آن به پوشش خدمات برای مدل‌های این برند اشاره شود:\n{models_str}"

        elif self.brief.page_level in [3, 4] and self.brief.entity and self.brief.entity.kind == TaxonomyNode.Kind.MODEL:
            model = self.brief.entity
            meta = model.meta
            taxonomy_context = f"""
[موجودیت هدف (Entity) و اطلاعات فنی (Context & Specs)]:
نام دقیق: {model.parent.name} {model.name}
تیپ‌ها و نام‌های رایج در بازار که باید در متن خروجی ذکر شوند.: {", ".join(meta.get("variations", []))}
نوع سیستم امنیتی (بسیار مهم برای اعتبار فنی): {meta.get("chip_type", "نامشخص")}
"""
        return taxonomy_context

    def _get_anti_cannibalization_context(self):
        if self.brief.page_level == 4:
            pillar_brief = PageBrief.objects.filter(
                project=self.project, entity=self.brief.entity, service_type=self.brief.service_type, page_level=3
            ).first()
            if pillar_brief:
                pillar_content = PageContent.objects.filter(page_brief=pillar_brief).first()
                if pillar_content:
                    existing_text = getattr(pillar_content, 'content', None) or getattr(pillar_content, 'outline_json', None)
                    if existing_text:
                        return f"""
<negative_constraints>
[⚠️ هشدار حیاتی سئو: ممنوعیت Keyword Cannibalization]
این صفحه یک "کلاستر" است که به صفحه والد خود لینک می‌دهد.
قانون قطعی: شما تحت هیچ شرایطی نباید مباحث اصلی مطرح شده در صفحه والد را در این مقاله تکرار یا بازنویسی کنید.
محتوای والد (فقط برای اطلاع - از تکرار این موارد اکیداً خودداری شود):
---
{str(existing_text)[:1500]}...
---
زاویه دید شما باید ۱۰۰٪ و منحصراً روی کلمه کلیدی '{self.brief.keyword.text}' متمرکز باشد.
</negative_constraints>
"""
        return ""

    def _get_planned_links_context(self):
        links = InternalLink.objects.filter(source_page=self.brief, status=InternalLink.Status.PLANNED)
        if not links.exists():
            return "لینک داخلی خاصی برای این صفحه برنامه‌ریزی نشده است."
        links_str = [f"- انکر تکست: '{link.anchor_text}' | دلیل: {link.source_reason}" for link in links]
        return "[شبکه لینک‌سازی داخلی برنامه‌ریزی شده]\nاین لینک‌ها را به صورت منطقی و در بلوک‌های مرتبط (فیلد internal_links_to_include) توزیع کنید:\n" + "\n".join(links_str)

    def _get_internal_links_mapping(self):
        """ساخت مپینگ لینک‌های داخلی همراه با Base Domain پروژه"""
        links = InternalLink.objects.filter(source_page=self.brief, status=InternalLink.Status.PLANNED)
        if not links.exists():
            return "هیچ لینک داخلی برای این صفحه برنامه‌ریزی نشده است."
            
        # استخراج دامنه اصلی از مدل Project و حذف اسلش اضافه از انتهای آن
        base_domain = self.project.base_domain.rstrip('/') if self.project.base_domain else ""
        
        links_list = []
        for link in links:
            target_path = link.target_page.url_path if link.target_page else "#"
            if target_path != "#" and not target_path.startswith('/'):
                target_path = '/' + target_path
                
            full_url = f"{base_domain}{target_path}"
            links_list.append(f"- Anchor Text: '{link.anchor_text}' | URL: {full_url}")
            
        return "\n".join(links_list)

    # ---------------------------------------------------------
    # متدهای تولید پرامپت ایجنت‌ها
    # ---------------------------------------------------------
        
    def get_planner_prompt(self):
            """ساخت پرامپت نهایی برای ایجنت Planner"""
            system_template = """شما یک 'مدیر استراتژی محتوا' و 'آرشیتکت ارشد سئو' هستید.
    وظیفه شما طراحی یک Outline ساختاریافته (JSON) برای نویسندگان (Writers) است.

    {anti_cannibalization_context}
    اطلاعات پایه صفحه:
    {intent_and_service_context}
    موجودیت‌ها:
    {taxonomy_context}
    لینک‌های داخلی تخصیص‌یافته:
    {links_context}

    [قوانین اکید و الزامی معماری بلوک‌ها]:
    1. ساخت کلیدواژه اصلی ترکیبی (Focus Keyword): کلمه کلیدی اصلی باید ترکیب صحیح و طبیعی از "سرویس + موجودیت (برند/مدل)" باشد (مثلا به جای کلمه خام، از "ساخت ریموت کلیک" یا "کیلس ایروکس" استفاده کنید). این ترکیب اگزکت باید در فیلد `focus_keyword`، تایتل سئو و h1 قرار گیرد و پلن بلوک hero بر اساس آن چیده شود.
    2. چالش حیاتی بودجه کلمات: مجموع کلمات این مقاله باید حداقل {total_word} کلمه باشد. برای رسیدن به این حجم، تعداد بلوک‌های کافی طراحی کنید.
    3. جلوگیری از کلیشه در شروع: بلوک 'hero' را طوری برنامه‌ریزی کنید که با یک دید جامع شروع شود و صرفاً روی سناریوی کلیشه‌ای "گم شدن ریموت" تمرکز نکند.
    4. ترتیب بلوک‌ها: اولین بلوک 'hero'، آخرین بلوک‌ها به ترتیب 'faq' و 'conclusion'.
    5. تگ‌های عنوان (SEO Title/H1): عناوین باید حرفه‌ای، دقیق و فاقد کلمات اضافه باشند.
    6. قانون تصویر صنعتی: یک بلوک 'image' با فیلد title حاوی Alt Text بنویسید.
    7. قانون بلوک Specs: در صورت نیاز فنی، یک بلوک 'specs' ایجاد کنید.
    """
            human_template = "لطفاً ساختار مقاله را برای کلمه کلیدی '{focus_keyword}' در فرمت JSON خواسته شده تولید کن."

            return ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template(human_template)
            ]).format_prompt(
                anti_cannibalization_context=self._get_anti_cannibalization_context(),
                intent_and_service_context=self._get_intent_and_service_context(),
                taxonomy_context=self._get_taxonomy_context(),
                links_context=self._get_planned_links_context(),
                total_word=self.brief.target_word_count,
                focus_keyword=self.brief.keyword.text
            )
    
    def get_writer_prompt(self, current_block: dict, previous_content_html: str, focus_keyword:str=None):
        """تولید پرامپت برای ایجنت Writer"""
        system_template = """<system_instructions>
                        <role>
                        شما یک «نویسنده ارشد محتوای سئو» (Senior SEO Content Writer) و «متخصص فنی موتورسیکلت» هستید.
                        ماموریت شما نگارش محتوای دقیق و باکیفیت **فقط برای یک بلوک مشخص** از یک مقاله جامع است، نه کل مقاله.
                        </role>

                        <context_data>
                        [اطلاعات استراتژیک صفحه]
                        {intent_and_service_context}

                        [موجودیت‌ها و اطلاعات فنی]
                        {taxonomy_context}

                        [سوابق محتوایی تولید شده در بلوک‌های قبلی]
                        <previous_content>
                        {previous_content}
                        </previous_content>
                        </context_data>

                        <general_writing_protocols>
                        1. [تخصص و لحن]: متن باید کاملاً تخصصی، معتبر و متناسب با Search Intent باشد. زاویه دید شما باید حرفه‌ای، جامع و مسلط بر تمام ابعاد خدمات (تعمیر، کپی، پروگرام و ساخت) باشد.
                        2. [بودجه کلمات - حیاتی]: بودجه کلمات بلوک به شما داده شده است. خلاصه‌نویسی اکیداً ممنوع است. شما موظفید با بسط دادن مفاهیم فنی، ارائه مثال‌های دقیق و توضیحات جامع، طول متن را دقیقاً به تارگت کلمات برسانید.
                        3. [کلمه کلیدی کانونی]: کلمه کلیدی اصلی '{focus_keyword}' (که ترکیب سرویس و مدل است) باید دقیقاً و عیناً در پاراگراف اولِ بلوک 'hero' جایگذاری شود.
                        4. [کلمات کلیدی کمکی]: کلمات کلیدی هدف این بلوک را به صورت کاملاً طبیعی در متن توزیع کنید.
                        5. [لینک‌دهی خارجی]: در صورت نیاز به لینک دادن کلمات تخصصی به منابع خارجی، حداکثر از ۱ یا ۲ لینک معتبر فارسی استفاده کنید.
                        </general_writing_protocols>

                        <negative_constraints>
                        شما تحت هیچ شرایطی اجازه تخطی از قوانین زیر را ندارید:
                        - ممنوعیت کلیشه: استفاده از شروع‌های زرد، کلیشه‌ای و بازاری (مثل "اگر ریموت موتور خود را گم کرده‌اید نگران نباشید...") اکیداً ممنوع است.
                        - ممنوعیت تکرار: بازگویی یا بازنویسی مفاهیمی که در <previous_content> آمده است، مطلقاً ممنوع است. فقط اطلاعات جدید اضافه کنید.
                        - ممنوعیت قیمت‌گذاری: درج هرگونه قیمت (ریالی، ارزی، حدودی یا دقیق) کاملاً ممنوع است.
                        - کلمات ممنوعه: استفاده از کلمه "ارزان" تحت هر شرایطی در متن ممنوع است.
                        - لینک‌دهی انگلیسی: لینک دادن به منابع غیرفارسی (مثل en.wikipedia.org) اکیداً ممنوع است.
                        </negative_constraints>

                        <block_type_instructions>
                        شما بر اساس متغیر نوع بلوک، باید **فقط یکی** از دستورالعمل‌های زیر را اجرا کنید:

                        <if_type_html>
                        اگر متغیر نوع بلوک برابر با متن استاندارد بود (مثل hero, text, conclusion):
                        - خروجی: فقط و فقط کد HTML معتبر (شامل تگ‌های p, ul, li, table, h3 و غیره).
                        - فرمت: هیچ تگ مارک‌داون (مثل ```html) در ابتدا و انتهای خروجی درج نکنید. متن باید مستقیماً قابل تزریق به دیتابیس باشد.
                        </if_type_html>

                        <if_type_faq>
                        اگر متغیر نوع بلوک برابر با "faq" بود:
                        - خروجی: تولید تگ HTML اکیداً ممنوع است. فقط باید یک آرایه JSON معتبر (به عنوان String) برگردانید.
                        - فرمت‌بندی: کاراکترهای نقل‌قول (") داخل متن جواب‌ها باید حتماً با بک‌اسلش (\\") فرار (Escape) داده شوند تا ساختار JSON نشکند. هیچ بک‌تیک مارک‌داونی (مثل ```json) قرار ندهید.
                        - نمونه ساختار دقیق:
                        [
                        {{"question": "سوال اول در مورد موجودیت؟", "answer": "پاسخ کوتاه و تخصصی سوال اول."}},
                        {{"question": "سوال دوم؟", "answer": "پاسخ تخصصی دوم."}}
                        ]
                        </if_type_faq>

                        <if_type_image>
                        اگر متغیر نوع بلوک برابر با "image" بود:
                        - خروجی: تولید هیچ‌گونه متن متفرقه، پاراگراف یا تگ HTML مجاز نیست.
                        - وظیفه: فقط و فقط یک رشته متنی کوتاه (بین ۵ تا ۱۰ کلمه) تولید کنید که به عنوان متن جایگزین (Alt Text) عکس صنعتی استفاده خواهد شد.
                        </if_type_image>

                        <if_type_specs>
                        اگر متغیر نوع بلوک برابر با "specs" بود:
                        - خروجی: تولید تگ HTML اکیداً ممنوع است. خروجی شما باید منحصراً یک آبجکت JSON معتبر (بدون بک‌تیک) حاوی مشخصات فنی ریموت باشد.
                        - نمونه ساختار دقیق:
                        {{"فرکانس کاری": "۴۳۳ مگاهرتز", "نوع چیپ": "ID46 ضدسرقت", "باتری": "CR2032"}}
                        </if_type_specs>
                        </block_type_instructions>
                        </system_instructions>
                        """

        human_template = """<block_assignment>
                        [مشخصات بلوک جاری برای نگارش]
                        - نوع بلوک (block_type): {block_type}
                        - عنوان بلوک (title): {block_title}
                        - هدف و نیت بلوک (purpose_and_intent): {block_purpose}
                        - بودجه کلمات: حدود {block_word_count} کلمه
                        - کلمات کلیدی هدف در این بلوک: {target_keywords}
                        - لینک‌های داخلی تخصیص‌یافته: {internal_links}

                        لطفاً محتوای این بلوک را دقیقاً مطابق با بخش <block_type_instructions> در دستورالعمل سیستم، تولید و ارائه کنید.
                        </block_assignment>"""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ]).format_prompt(
            intent_and_service_context=self._get_intent_and_service_context(),
            taxonomy_context=self._get_taxonomy_context(),
            previous_content=previous_content_html if previous_content_html else "این اولین بلوک مقاله است.",
            focus_keyword= focus_keyword or self.brief.keyword.text,
            block_type=current_block.get('block_type', ''),
            block_title=current_block.get('title', ''),
            block_purpose=current_block.get('purpose_and_intent', ''),
            block_word_count=current_block.get('block_word_count', 0),
            target_keywords=", ".join(current_block.get('target_keywords', [])),
            internal_links=", ".join(current_block.get('internal_links_to_include', []))
        )

    def get_seo_reviewer_prompt(self, generated_blocks: List[Dict[str, Any]]):
        """تولید پرامپت برای ایجنت SEO Reviewer"""
        system_template = """شما یک 'سرممیز ارشد سئو (SEO Auditor)' و 'تحلیل‌گر محتوا' هستید.
وظیفه شما بررسی دقیق و سخت‌گیرانه محتوای تولید شده توسط نویسندگان است.

اطلاعات پایه صفحه:
{intent_and_service_context}

موجودیت‌ها و اطلاعات فنی (Context & Specs):
{taxonomy_context}

[چک‌لیست ممیزی سخت‌گیرانه]:
1. آنالیز توزیع فوکوس کیورد: کلمه کلیدی اصلی '{focus_keyword}' حتماً باید در ۳۰٪ ابتدایی بلوک هیرو/مقدمه به صورت طبیعی درج شده باشد.
2. ممیزی چگالی معنایی (TF-IDF): کلمات کلیدی کمکی و ال‌اس‌آی (LSI) باید در بدنه متون پخش شده باشند.
3. تبصره اطلاعات فنی (Technical Specs): اطلاعات دقیق فنی مانند فرکانس، نوع باتری و چیپ ایموبیلایزر که در بخش (Context & Specs) داده شده، در یک باکس گرافیکی مجزا در سایت رندر می‌شوند. بنابراین اگر این کلمات مستقیماً در متن پاراگراف‌ها تکرار نشده بودند، نباید نمره منفی بدهی.
4. تبصره جداول قیمت (Pricing Policy): به دلیل نوسانات بازار ایران، استفاده از عباراتی نظیر "استعلام تلفنی"، "تماس بگیرید" یا "بر اساس مدل" در جداول قیمت کاملاً استاندارد و مورد تایید است. به هیچ وجه برای نبود عدد دقیق قیمت نمره منفی نده.
5. عدم تکرار در تایتل‌ها: تایتل‌ها نباید درون کانتنت تکرار شوند.

اگر بلوکی معیارهای بالا را نقض کرده، شناسه دقیق آن (block_id) را در فیلد failed_blocks قرار داده و یک راهنمای صریح برای نویسنده بنویسید. خروجی شما باید منحصراً یک ساختار JSON معتبر باشد.
"""
        content_for_review = "".join([f"\n{'='*40}\n[شناسه بلوک: {b.get('block_id', i)}] | [نوع: {b.get('block_type', '')}] | [عنوان: {b.get('title', '')}]\n{'-'*40}\n{b.get('content', '')}\n" for i, b in enumerate(generated_blocks)])

        human_template = "محتوای تولید شده برای بررسی:\n{generated_content}\nلطفا این محتوا را بررسی کرده و خروجی ساختاریافته را ارائه دهید."

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ]).format_prompt(
            intent_and_service_context=self._get_intent_and_service_context(),
            taxonomy_context=self._get_taxonomy_context(),
            focus_keyword=self.brief.keyword.text,
            generated_content=content_for_review
        )

    def get_humanizer_prompt(self, generated_blocks: List[Dict[str, Any]]):
            """تولید پرامپت ایجنت بازنویسی (برای اجرای یکباره روی کل بلوک‌ها)"""
            system_template = """شما یک 'ویراستار ارشد (Senior Editor)' هستید.
    وظیفه شما دریافت بلوک‌های متنی و بازنویسی آن‌ها برای رفع لحن رباتیک هوش مصنوعی است.

    [قوانین بسیار مهم ویرایش - قفل‌های حیاتی]:
    1. قفل طول متن (بسیار مهم): شما اکیداً حق خلاصه‌سازی، ادغام پاراگراف‌ها، حذف اطلاعات یا کاهش تعداد کلمات را ندارید! طول متن خروجی شما برای هر بلوک باید دقیقاً هم‌اندازه یا بیشتر از متن ورودی باشد. وظیفه شما فقط "تغییر لحن" است، نه کوتاه کردن متن.
    2. رفع لحن رباتیک: عبارات متداول هوش مصنوعی (مثل "در نتیجه"، "دنیای امروز"، "شایان ذکر است") را حذف یا محاوره‌ای کنید.
    3. حفظ سئو و تگ‌ها: تمام تگ‌های HTML (مثل h2, p, strong, ul) و کلمات کلیدی هدف باید عیناً و بدون تغییر حفظ شوند.
    4. بلوک‌های JSON (faq یا specs): ساختار حفظ شود، فقط مقادیر متنی روان‌تر شوند.
    5. بلوک‌های تصویری (image): به این بلوک‌ها دست نزنید و عیناً برگردانید.
    6. خروجی باید آرایه‌ای معتبر از تمام بلوک‌ها باشد که شناسه (block_id) آن‌ها حفظ شده است.
    """
            content_for_review = ""
            for b in generated_blocks:
                content_for_review += f"\n--- [block_id: {b.get('block_id')}] | [block_type: {b.get('block_type')}] ---\n{b.get('content')}\n"

            human_template = """محتوای تمام بلوک‌ها جهت ویرایش لحن:

    {content}

    لطفاً تمام بلوک‌ها را بررسی کرده و با رعایت اکید "قانون حفظ طول متن"، خروجی را تحویل دهید."""

            return ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template(human_template)
            ]).format_prompt(content=content_for_review)

    def get_link_builder_prompt(self, final_html_content: str):
        """تولید پرامپت برای ایجنت Link Builder"""
        system_template = """<system_instructions>
        <role_and_objective>
        شما یک «متخصص ارشد لینک‌سازی سئو» (Senior SEO Link Builder) و «توسعه‌دهنده وب» هستید.
        ماموریت شما دریافت کد HTML خام یک مقاله کامل و تزریق دقیق، هوشمندانه و طبیعیِ لینک‌های داخلی و خارجی به درون آن است.
        </role_and_objective>

        <context_data>
        [لیست لینک‌های داخلی تخصیص‌یافته]
        {internal_links_map}

        [دیتابیس بومی لینک‌های خارجی سئو]
        {external_links_map}
        </context_data>

        <execution_protocols>
        1. [تزریق لینک داخلی]: شما موظف هستید دقیقاً و عیناً از Anchor Text های ارائه شده استفاده کنید (حتی اگر طولانی یا غیرمعمول به نظر برسند). فرمت استاندارد: <a href="URL">Anchor Text</a>.
        2. [انطباق متنی (Natural Flow)]: برای اینکه انکرتکست به صورت طبیعی در جمله بنشیند، شما مجاز هستید نهایتاً ۳ الی ۴ کلمه در اطراف محل جایگذاری لینک را ویرایش کنید یا تغییر دهید.
        3. [تزریق لینک خارجی]: اگر کلمات موجود در دیتابیس لینک‌های خارجی در متن وجود داشتند، آن‌ها را به آدرس‌های مشخص شده لینک دهید. سقف استفاده از لینک خارجی: **حداکثر ۱ تا ۲ عدد در کل مقاله**.
        </execution_protocols>

        <negative_constraints>
        [⚠️ قفل کانتکست و هشدارهای امنیتی حیاتی ⚠️]
        شما تحت هیچ شرایطی اجازه تخطی از موارد زیر را ندارید:
        - ممنوعیت تخریب محتوا: شما حق حذف، خلاصه‌سازی، بازنویسی کلی یا تغییر ساختار HTML مقاله اصلی را ندارید. تمام پاراگراف‌ها، تگ‌ها و لیست‌ها باید ۱۰۰٪ دست‌نخورده باقی بمانند.
        - حریم کلیدواژه کانونی: هرگز کلمه کلیدی اصلی مقاله که درون تگ <strong> قرار دارد را با تگ لینک (<a>) قطع نکنید یا تداخل ایجاد نکنید.
        - ممنوعیت لینک فیک/انگلیسی: تولید و درج هرگونه لینک خارجی خارج از دیتابیس داده شده، لینک‌های نامعتبر یا انگلیسی (مثل en.wikipedia.org) اکیداً ممنوع است.
        </negative_constraints>

        <output_format>
        [الزامات سخت‌گیرانه خروجی JSON]
        خروجی شما باید منحصراً و فقط یک آبجکت JSON معتبر باشد که در فیلد `linked_html` آن، کد HTML نهایی و اصلاح‌شده قرار گرفته است.
        - ممنوعیت مارک‌داون: استفاده از بک‌تیک مارک‌داون (مثل ```json) در ابتدا و انتهای خروجی اکیداً ممنوع است. سیستم مستقیماً خروجی را به عنوان JSON می‌خواند.
        - قانون فرار کاراکترها (Escaping): از آنجا که محتوای شما HTML است، تمامی کاراکترهای نقل‌قول مضاعف (") داخل تگ‌های HTML (مثل href یا class) باید حتماً با بک‌اسلش (\\") اسکیپ شوند تا ساختار JSON نشکند.

        نمونه خروجی کاملاً معتبر:
        {{"linked_html": "<p>این یک متن نمونه است که در آن <a href=\\"[https://example.com](https://example.com)\\">لینک داخلی</a> قرار داده شده است.</p>"}}
        </output_format>
        </system_instructions>"""

        human_template = """<article_data>
        کد HTML اصلی مقاله (بدون لینک) جهت عملیات تزریق لینک:
        <raw_html>
        {html_content}
        </raw_html>

        لطفاً تمام لینک‌های داخلی و خارجی را بر اساس پروتکل‌ها و محدودیت‌های گفته شده درون این متن تزریق کنید و خروجی را صرفاً در فرمت JSON تحویل دهید.
        </article_data>"""
        external_map_str = "\n".join([f"- کلمه: '{k}' | آدرس: {v}" for k, v in EXTERNAL_LINKS_MAP.items()])

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ]).format_prompt(
            internal_links_map=self._get_internal_links_mapping(),
            external_links_map=external_map_str,
            html_content=final_html_content
        )

    def get_hero_writer_prompt(self, current_block: dict, focus_keyword:str):
        """تولید پرامپت اختصاصی برای ایجنت کپی‌رایتر (فقط برای بلوک هیرو)"""
        system_template = """شما یک 'کپی‌رایتر ارشد (Copywriter)' و 'متخصص فروش خدمات' هستید.
وظیفه شما نوشتن **فقط بخش مقدمه (Hero)** برای یک لندینگ‌پیج است. 

اطلاعات پایه صفحه:
{intent_and_service_context}

موجودیت هدف:
{taxonomy_context}

[قوانین اکید کپی‌رایتینگ برای هیرو]:
1. لحن و قلاب (Hook): لحن شما باید صمیمی، اطمینان‌بخش، انسانی و کاملاً تجاری باشد. از جملات خشک، دانشگاهی و رباتیک (مثل "مقدمه‌ای بر...", "در دنیای امروز...", "همانطور که می‌دانیم") به شدت پرهیز کنید.
2. درک درد کاربر: مخاطب شما کسی است که یا ریموتش را گم کرده و استرس دارد، یا به یک ریموت یدک نیاز دارد یا موتور سیکلتش با ریموت روشن نمی شود. مستقیماً به نیاز او اشاره کنید و به او اطمینان دهید که در سریع‌ترین زمان مشکلش با دستگاه‌های پیشرفته حل می‌شود.
3. کلمه کلیدی اگزکت: کلمه کلیدی اصلی '{focus_keyword}' باید **دقیقاً و بدون حتی یک حرف اضافه** در جمله اول یا نهایتاً دوم به صورت کاملا طبیعی قرار بگیرد.
4. عدم استفاده از تگ هدر: شما حق استفاده از تگ‌های <h2> یا <h3> را ندارید! خروجی شما باید مستقیماً با پاراگراف <p> شروع شود.
5. استایل‌دهی: کلمات مهم، نام مدل موتور و ویژگی‌های کلیدی خدمات (مثل در محل، بدون باز کردن فلاپ، با دستگاه دیاگ) را درون تگ <strong> قرار دهید تا چشم کاربر را بگیرد.
6. طول متن: حداکثر در حدود {block_word_count} کلمه بنویسید (نه خیلی کوتاه، نه خیلی طولانی و خسته‌کننده).
"""
        human_template = """کلمه کلیدی هدف: {focus_keyword}
بودجه کلمات: حدود {block_word_count} کلمه
کلمات کمکی که بهتر است در متن باشند: {target_keywords}

لطفاً یک متن هیروی جذاب، انسانی و میخکوب‌کننده برای این صفحه بنویس."""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ]).format_prompt(
            intent_and_service_context=self._get_intent_and_service_context(),
            taxonomy_context=self._get_taxonomy_context(),
            focus_keyword=focus_keyword,
            block_word_count=current_block.get('block_word_count', 100),
            target_keywords=", ".join(current_block.get('target_keywords', []))
        )
    