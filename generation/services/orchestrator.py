# generation/services/orchestrator.py
import os
import json
import re
import traceback
from django.conf import settings
from django.utils import timezone

from content.models import PageContent
from generation.services.schema_generator import generate_advanced_schema
from generation.agents.prompt_manager import (
    PromptManager, PageOutline, WriterOutput, 
    SEOAuditResult, HumanizerOutput, LinkBuilderOutput
)
from generation.utils.llm_manager import get_llm

class ContentOrchestratorService:
    MAX_ITERATIONS = 3 

    def __init__(self, page_content: PageContent):
        self.content_obj = page_content
        self.brief = page_content.page_brief
        self.prompt_manager = PromptManager(self.brief)
        
        self.planner_llm = get_llm(temperature=0.2).with_structured_output(PageOutline)
        self.writer_llm = get_llm(temperature=0.4).with_structured_output(WriterOutput)
        self.seo_llm = get_llm(temperature=0.1).with_structured_output(SEOAuditResult)
        self.humanizer_llm = get_llm(temperature=0.5).with_structured_output(HumanizerOutput)
        self.link_llm = get_llm(model_name="gemini-3.1-flash-lite", temperature=0.0).with_structured_output(LinkBuilderOutput)

    def _log_prompt(self, agent_name: str, prompt_value):
        try:
            log_dir = os.path.join(settings.BASE_DIR, 'logs', 'prompts', str(self.content_obj.id))
            os.makedirs(log_dir, exist_ok=True)
            
            file_path = os.path.join(log_dir, f"{agent_name}_iter_{self.content_obj.iterations}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(prompt_value.to_string())
        except Exception as e:
            print(f"Failed to log prompt for {agent_name}: {e}")

    def _log_error(self, step: str, error_msg: str):
        self.content_obj.generation_error = f"Error in [{step}]: {error_msg}"
        self.content_obj.generation_status = PageContent.GenerationStatus.FAILED
        self.content_obj.save()

    def run(self):
        try:
            # ---------------------------------------------------------
            # 1. PLANNER STAGE
            # ---------------------------------------------------------
            if self.content_obj.generation_status == PageContent.GenerationStatus.PENDING:
                self.content_obj.generation_status = PageContent.GenerationStatus.PLANNING
                self.content_obj.save()

                prompt = self.prompt_manager.get_planner_prompt()
                self._log_prompt("1_Planner", prompt)
                
                print(f"[{self.content_obj.id}] Running Planner Agent...")
                outline: PageOutline = self.planner_llm.invoke(prompt.to_messages())
                
                self.content_obj.seo_title = outline.seo_title
                self.content_obj.meta_description = outline.meta_description
                self.content_obj.h1 = outline.h1_title
                self.content_obj.focus_keyword = outline.focus_keyword
                self.content_obj.outline_json = outline.model_dump()
                self.content_obj.generation_status = PageContent.GenerationStatus.WRITING
                self.content_obj.save()

            # ---------------------------------------------------------
            # 2. WRITER STAGE
            # ---------------------------------------------------------
            # ---------------------------------------------------------
            # 2. WRITER STAGE (هوشمند شده)
            # ---------------------------------------------------------
            if self.content_obj.generation_status == PageContent.GenerationStatus.WRITING:
                print(f"[{self.content_obj.id}] Running Writer Agents...")
                outline_data = self.content_obj.outline_json
                blocks = outline_data.get('blocks', [])
                
                generated_blocks = []
                accumulated_html = ""
                total_blocks = len(blocks)

                for idx, block in enumerate(blocks):
                    b_type = block.get("block_type", "")
                    b_title = block.get("title", "بدون عنوان")
                    print(f"[{self.content_obj.id}] Processing Block {idx + 1}/{total_blocks} -> Type: {b_type} | Title: {b_title}")
                    
                    content_str = ""

                    # --- حالت اول: بلوک تصویر (Bypass LLM) ---
                    if b_type == "image":
                        # نیازی به هوش مصنوعی نیست! عنوان یا هدف بلوک را به عنوان Alt Text در نظر می‌گیریم
                        content_str = block.get("title") or block.get("purpose_and_intent") or "تصویر مرتبط با خدمات"
                        print(f"[{self.content_obj.id}] ⚡ Bypassing LLM for image block. Alt text extracted.")

                    # --- حالت دوم: بلوک هیرو (اختصاصی کپی‌رایتر) ---
                    elif b_type == "hero":
                        print(f"[{self.content_obj.id}] this is hero agent")
                        prompt = self.prompt_manager.get_hero_writer_prompt(current_block=block, focus_keyword=self.content_obj.focus_keyword)
                        self._log_prompt(f"2_Writer_Hero", prompt)
                        # استفاده از دمای بالاتر (مثلا 0.6) برای خلاقیت بیشتر در کپی‌رایتینگ (اختیاری)
                        hero_out: WriterOutput = self.writer_llm.invoke(prompt.to_messages())
                        content_str = hero_out.content
                    
                    # --- حالت سوم: سایر بلوک‌ها (رایتر فنی) ---
                    else:
                        prompt = self.prompt_manager.get_writer_prompt(current_block=block, previous_content_html=accumulated_html, focus_keyword=self.content_obj.focus_keyword)
                        self._log_prompt(f"2_Writer_Block_{idx}", prompt)
                        
                        writer_out: WriterOutput = self.writer_llm.invoke(prompt.to_messages())
                        content_str = writer_out.content

                        # اضافه کردن اجباری H2 اگر هوش مصنوعی جا انداخته بود (به جز برای faq و specs)
                        if b_type not in ["faq", "specs"]:
                            if not any(tag in content_str.lower() for tag in ["<h1", "<h2", "<h3", "<h4"]):
                                if b_title:
                                    content_str = f"<h2>{b_title}</h2>\n" + content_str

                    # ذخیره خروجی نهایی بلوک در آرایه
                    generated_blocks.append({
                        "block_id": idx,
                        "block_type": b_type,
                        "title": b_title,
                        "content": content_str
                    })
                    
                    # اضافه کردن متن به سوابق (تصاویر را به سوابق نمی‌دهیم تا مدل گیج نشود)
                    if b_type != "image":
                        accumulated_html += f"\n<!-- Block {idx}: {b_type} -->\n{content_str}\n"

                self.content_obj.blocks_json = generated_blocks
                self.content_obj.generation_status = PageContent.GenerationStatus.REVIEWING
                self.content_obj.save()

            # ---------------------------------------------------------
            # 3. SEO REVIEWER STAGE
            # ---------------------------------------------------------
            if self.content_obj.generation_status == PageContent.GenerationStatus.REVIEWING:
                print(f"[{self.content_obj.id}] Running SEO Reviewer Agent...")
                generated_blocks = self.content_obj.blocks_json
                
                prompt = self.prompt_manager.get_seo_reviewer_prompt(generated_blocks)
                self._log_prompt("3_SEO_Reviewer", prompt)
                
                seo_result: SEOAuditResult = self.seo_llm.invoke(prompt.to_messages())
                
                self.content_obj.seo_score = seo_result.score
                self.content_obj.seo_report = seo_result.model_dump()
                
                if not seo_result.is_approved:
                    print(f"[{self.content_obj.id}] SEO Failed! Score: {seo_result.score}. Iteration: {self.content_obj.iterations}")
                    self.content_obj.iterations += 1
                    
                    logs = self.content_obj.agent_logs if isinstance(self.content_obj.agent_logs, list) else []
                    logs.append({
                        "iteration": self.content_obj.iterations,
                        "report": seo_result.summary_report,
                        "failed_blocks": [fb.model_dump() for fb in seo_result.failed_blocks]
                    })
                    self.content_obj.agent_logs = logs
                    
                    if self.content_obj.iterations >= self.MAX_ITERATIONS:
                        self._log_error("SEO_Review", "Max iterations reached. SEO standards not met.")
                        return False
                    
                    self.content_obj.generation_status = PageContent.GenerationStatus.WRITING
                    self.content_obj.save()
                    return self.run()
                else:
                    self.content_obj.save()

            # ---------------------------------------------------------
            # 4. HUMANIZER STAGE 
            # ---------------------------------------------------------
            print(f"[{self.content_obj.id}] Running Humanizer Agent on ALL blocks simultaneously...")
            generated_blocks = self.content_obj.blocks_json
            
            prompt = self.prompt_manager.get_humanizer_prompt(generated_blocks)
            self._log_prompt("4_Humanizer_All_Blocks", prompt)
            
            human_out: HumanizerOutput = self.humanizer_llm.invoke(prompt.to_messages())
            
            humanized_map = {b.block_id: b.humanized_content for b in human_out.blocks}
            
            for block in generated_blocks:
                b_id = block.get("block_id")
                if b_id in humanized_map:
                    block["content"] = humanized_map[b_id]
                
            self.content_obj.blocks_json = generated_blocks
            self.content_obj.save()

            # ---------------------------------------------------------
            # 5. LINK BUILDER & FINAL JSON MAPPING
            # ---------------------------------------------------------
            print(f"[{self.content_obj.id}] Running Link Builder Agent...")
            
            final_html_parts = []
            faq_data = []
            
            for block in self.content_obj.blocks_json:
                b_type = block.get("block_type")
                b_content = block.get("content")
                b_id = block.get("block_id", 0)
                
                if b_type == "faq":
                    try:
                        parsed_faq = json.loads(b_content)
                        faq_data.extend(parsed_faq)
                    except json.JSONDecodeError:
                        pass
                
                # بلوک‌ها را داخل یک div با id مشخص قرار می‌دهیم تا پس از لینک‌سازی بتوانیم تفکیکشان کنیم
                final_html_parts.append(f'<div id="block-{b_id}">\n{b_content}\n</div>')

            self.content_obj.faq_json = faq_data
            full_html = "\n".join(final_html_parts)
            
            prompt = self.prompt_manager.get_link_builder_prompt(full_html)
            self._log_prompt("5_Link_Builder", prompt)
            
            link_out: LinkBuilderOutput = self.link_llm.invoke(prompt.to_messages())
            linked_full_html = link_out.linked_html
            
            # استخراج مجدد بلوک‌های لینک‌دار شده و آپدیت blocks_json
            for block in self.content_obj.blocks_json:
                b_id = block.get("block_id")
                
                # پیدا کردن محتوای تغییریافته هر بلوک بوسیله Regex
                pattern = re.compile(rf'<div id="block-{b_id}">\s*(.*?)\s*</div>', re.DOTALL)
                match = pattern.search(linked_full_html)
                
                if match:
                    block["content"] = match.group(1).strip()
            
            # ⚠️ اعمال قانون مهم: خالی گذاشتن کامل فیلد compiled_body
            self.content_obj.compiled_body = "" 

            print(f"[{self.content_obj.id}] schema generating...")
            schemas_list = generate_advanced_schema(self.brief, self.content_obj)
            self.content_obj.schema_json = json.dumps(schemas_list, ensure_ascii=False)
            self.content_obj.generation_status = PageContent.GenerationStatus.COMPLETED
            self.content_obj.generated_at = timezone.now()
            self.content_obj.generated_by = "Multi-Agent System (Gemini 1.5)"
            self.content_obj.save()

            print(f"[{self.content_obj.id}] GENERATION COMPLETED SUCCESSFULLY! Output saved in blocks_json.")
            return True

        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Orchestrator Error on Page {self.content_obj.id}:\n{error_trace}")
            self._log_error("Orchestrator_Run", error_trace)
            return False
        