# content/services/pagebrief_sync.py
import random
from collections import defaultdict

from django.db import transaction
from django.utils.text import slugify

from core.models import Project
from taxonomy.models import ServiceType, TaxonomyNode
from content.models import Keyword, PageBrief, PageContent, InternalLink


AUTO_SOURCE = "auto:pagebrief_sync"


def s(v):
    return " ".join(str(v).replace("،", " ").split()).strip()

# ==========================================
# توابع تولید URL
# ==========================================
def root_url(service):
    return f"/{service.slug}/"

def city_url(service, city):
    return f"/{service.slug}/{city.slug}/"

def pillar_url(entity, keyword=None, is_master=False):
    chain = []
    cur = entity
    while cur and cur.kind != TaxonomyNode.Kind.CITY:
        chain.append(cur.slug)
        cur = cur.parent
    chain.reverse()
    
    base = "/remotes/" + "/".join(chain) + "/"
    if not is_master and keyword:
        slug = slugify(keyword.text.split(',')[0], allow_unicode=True)
        return base + f"{slug}/"
    return base

def cluster_url(entity, keyword, parent_keyword=None, is_parent_master=False):
    chain = []
    cur = entity
    while cur and cur.kind != TaxonomyNode.Kind.CITY:
        chain.append(cur.slug)
        cur = cur.parent
    chain.reverse()
    
    base = "/remotes/" + "/".join(chain) + "/"
        
    slug = slugify(keyword.text.split(',')[0], allow_unicode=True)
    return base + f"{slug}/"

# ==========================================
# توابع کمکی
# ==========================================
def root_text(service):
    return s(service.root_keyword or service.name)

def ensure_content(pagebrief: PageBrief):
    return PageContent.objects.update_or_create(
        page_brief=pagebrief,
        defaults={
            "slug": "", 
            "seo_title": "",
            "h1": "",
            "meta_description": "",
            "blocks_json": "",
            "outline_json": {},
            "faq_json": [],
            "schema_json": {},
            "generation_status": PageContent.GenerationStatus.PENDING,
            "publish_status": PageContent.PublishStatus.DRAFT,
            "target_server_post_id": None,
            "target_url": pagebrief.full_url, 
            "generated_by": "",
            "generation_error": "",
        },
    )[0]

def upsert_pagebrief(project, keyword, entity=None, page_level=0, page_type=PageBrief.PageType.PILLAR,
                     url_path="", parent_page=None, canonical_url="", target_word_count=2000):
    if not keyword:
        return None

    pb, created = PageBrief.objects.update_or_create(
        project=project,
        entity=entity,
        keyword=keyword,
        page_level=page_level,
        defaults={
            "page_type": page_type,
            "url_path": url_path,
            "canonical_url": canonical_url,
            "target_word_count": target_word_count,
            "parent_page": parent_page,
            "status": PageBrief.Status.GENERATED,
            "locked": False,
            "is_active": True,
        },
    )
    if not created and not pb.locked:
        dirty = False
        if pb.page_type != page_type:
            pb.page_type = page_type; dirty = True
        if pb.url_path != url_path:
            pb.url_path = url_path; dirty = True
        if pb.canonical_url != canonical_url:
            pb.canonical_url = canonical_url; dirty = True
        if pb.parent_page_id != (parent_page.id if parent_page else None):
            pb.parent_page = parent_page; dirty = True
        if pb.target_word_count != target_word_count:
            pb.target_word_count = target_word_count; dirty = True
            
        if dirty:
            pb.save()
            
    ensure_content(pb)
    return pb

def get_varied_anchor(cluster_url_path, pillar_kw_text, entity_name):
    exact_match = f"{pillar_kw_text} {entity_name}".strip()

    formats = [
        "{exact}",
        "{exact}",
        "مرکز تخصصی {exact}",
        "خدمات حرفه‌ای {exact}",
        "اطلاعات کامل درباره {exact}",
        "تعمیرات و خدمات {exact}",
        "نمایندگی خدمات {exact}",
        "سوئیچ و {exact}",
        "سیستم قفل و {exact}",
        "برای خدمات {entity} کلیک کنید",
        "بیشتر بخوانید: صفحه اختصاصی {entity}",
    ]

    idx = abs(hash(cluster_url_path)) % len(formats)
    return formats[idx].format(exact=exact_match, entity=entity_name)

# ==========================================
# گراف هوشمند لینک‌سازی داخلی (بهینه‌سازی شده)
# ==========================================
def build_links(project: Project):
    # پاکسازی لینک‌های خودکار قبلی پروژه جهت بازسازی گراف جدید
    InternalLink.objects.filter(source_page__project=project, source_reason=AUTO_SOURCE).delete()

    pages = list(PageBrief.objects.filter(project=project, is_active=True).select_related("keyword", "entity", "parent_page"))
    
    l3_clusters = [p for p in pages if p.page_level == 3]
    l2_pillars = [p for p in pages if p.page_level == 2 and p.page_type == PageBrief.PageType.PILLAR]
    l1_pillars = [p for p in pages if p.page_level == 1 and p.page_type == PageBrief.PageType.PILLAR]
    l0_pillars = [p for p in pages if p.page_level == 0 and p.page_type == PageBrief.PageType.PILLAR]

    l2_pillars_by_model = defaultdict(list)
    for p in l2_pillars:
        if p.entity_id:
            l2_pillars_by_model[p.entity_id].append(p)

    def safe_link(src, tgt, anchor, rel_type):
        if src.id == tgt.id:
            return
        InternalLink.objects.get_or_create(
            source_page=src, target_page=tgt, anchor_text=anchor,
            defaults={'relation_type': rel_type, 'source_reason': AUTO_SOURCE}
        )

    # ۱. لینک عمودی: لایه ۳ (کلاسترها) به تمام صفحات پیلار مدل خودشان در لایه ۲
    for cluster in l3_clusters:
        if cluster.entity_id:
            model_pillars = l2_pillars_by_model.get(cluster.entity_id, [])
            for pillar in model_pillars:
                anchor = get_varied_anchor(cluster.url_path, pillar.keyword.text, pillar.entity.name)
                safe_link(cluster, pillar, anchor, InternalLink.RelationType.VERTICAL)

    # ۲. لینک عمودی: لایه ۲ (مدل‌ها) به پیلار والد لایه ۱ (برند)
    for pillar in l2_pillars:
        if pillar.entity and pillar.entity.parent_id:
            l1_parent = next((p for p in l1_pillars if p.entity_id == pillar.entity.parent_id), None)
            if l1_parent:
                anchor = f"مرکز ریموت {l1_parent.entity.name}"
                safe_link(pillar, l1_parent, anchor, InternalLink.RelationType.VERTICAL)

    # ۳. لینک عمودی: لایه ۱ (برندها) به تمام صفحات لایه ۰ (ریشه/مادر)
    for l1 in l1_pillars:
        for l0 in l0_pillars:
            anchor = l0.keyword.text
            safe_link(l1, l0, anchor, InternalLink.RelationType.VERTICAL)

    # ۴. لینک افقی: صفحات لایه ۰ به یکدیگر
    if len(l0_pillars) > 1:
        for a, b in zip(l0_pillars, l0_pillars[1:] + [l0_pillars[0]]):
            safe_link(a, b, b.keyword.text, InternalLink.RelationType.HORIZONTAL)
            safe_link(b, a, a.keyword.text, InternalLink.RelationType.HORIZONTAL)

    # ۵. لینک افقی: صفحات لایه ۱ (برندها) به یکدیگر
    if len(l1_pillars) > 1:
        for a, b in zip(l1_pillars, l1_pillars[1:] + [l1_pillars[0]]):
            anchor_b = f"{b.keyword.text} {b.entity.name}" if b.entity else b.keyword.text
            anchor_a = f"{a.keyword.text} {a.entity.name}" if a.entity else a.keyword.text
            safe_link(a, b, anchor_b, InternalLink.RelationType.HORIZONTAL)
            safe_link(b, a, anchor_a, InternalLink.RelationType.HORIZONTAL)

    # ۶. لینک افقی اصلاح شده: برای هر مدل (Entity)، صفحات پیلار خودش کاملا زنجیره افقی تشکیل می‌دهند
    for model_id, model_list in l2_pillars_by_model.items():
        if len(model_list) > 1:
            for a, b in zip(model_list, model_list[1:] + [model_list[0]]):
                anchor_text_b = f"{b.keyword.text} {b.entity.name}" if b.entity else b.keyword.text
                anchor_text_a = f"{a.keyword.text} {a.entity.name}" if a.entity else a.keyword.text
                safe_link(a, b, anchor_text_b, InternalLink.RelationType.HORIZONTAL)
                safe_link(b, a, anchor_text_a, InternalLink.RelationType.HORIZONTAL)

    # ۷. لینک افقی اصلاح شده: مدل‌های دیگر در لایه ۲ که کلیدواژه مشترک دارند به هم لینک افقی می‌دهند
    l2_by_keyword = defaultdict(list)
    for p in l2_pillars:
        l2_by_keyword[p.keyword_id].append(p)
        
    for kw_id, kw_list in l2_by_keyword.items():
        if len(kw_list) > 1:
            for a, b in zip(kw_list, kw_list[1:] + [kw_list[0]]):
                # اگر دو صفحه از دو مدل متفاوت باشند، ارتباط افقی کلیدواژه مشترک برقرار می‌شود
                if a.entity_id != b.entity_id:
                    anchor_text_b = f"{b.keyword.text} {b.entity.name}" if b.entity else b.keyword.text
                    anchor_text_a = f"{a.keyword.text} {a.entity.name}" if a.entity else a.keyword.text
                    safe_link(a, b, anchor_text_b, InternalLink.RelationType.HORIZONTAL)
                    safe_link(b, a, anchor_text_a, InternalLink.RelationType.HORIZONTAL)

# ==========================================
# تابع اصلی همگام‌سازی پروژه
# ==========================================
@transaction.atomic
def sync_project(project: Project, keyword_ids=None, entity_ids=None, rebuild_links=True):
    services = list(ServiceType.objects.filter(project=project, is_active=True))
    root_pages, entity_pages, keyword_pages = [], [], []

    brand_hub_kw, _ = Keyword.objects.get_or_create(
        project=project, text="ریموت", 
        defaults={"status": Keyword.Status.CLASSIFIED, "priority_score": 100, "source": AUTO_SOURCE}
    )

    kws = list(Keyword.objects.filter(project=project, status=Keyword.Status.CLASSIFIED).select_related("service", "intent", "parent_keyword"))
    
    layer2_pillars_kws = [kw for kw in kws if kw.is_pillar]
    cluster_keywords = [kw for kw in kws if not kw.is_pillar]

    entities_qs = TaxonomyNode.objects.filter(project=project, is_active=True).select_related("parent")
    if entity_ids is not None:
        entities_qs = entities_qs.filter(id__in=entity_ids)
    entities = list(entities_qs)
    
    brands = [e for e in entities if e.kind == TaxonomyNode.Kind.BRAND]
    models = [e for e in entities if e.kind == TaxonomyNode.Kind.MODEL]
    cities = [e for e in entities if e.kind == TaxonomyNode.Kind.CITY]

    root_texts = set()

    # ==========================================
    # 1. لایه ۰: پیلارهای سرویس مادر و کلاسترهای شهر
    # ==========================================
    for service in services:
        root_txt = s(service.root_keyword or service.name)
        root_texts.add(root_txt)
        kw_root, _ = Keyword.objects.get_or_create(project=project, text=root_txt, defaults={"service": service, "priority_score": 100, "source": AUTO_SOURCE})
        if kw_root.service_id != service.id:
            kw_root.service = service
            kw_root.save()

        pb_root = upsert_pagebrief(
            project=project, keyword=kw_root, entity=None, page_level=0, page_type=PageBrief.PageType.PILLAR, 
            url_path=root_url(service), parent_page=None, target_word_count=3000
        )
        if pb_root: root_pages.append(pb_root)

        canonical_to_root = f"{project.base_domain.rstrip('/')}{pb_root.url_path}" if pb_root else ""
        for city in cities:
            pb_city = upsert_pagebrief(
                project=project, keyword=kw_root, entity=city, page_level=1, page_type=PageBrief.PageType.CLUSTER, 
                url_path=city_url(service, city), parent_page=pb_root, canonical_url=canonical_to_root,
                target_word_count=random.randint(1500, 2000)
            )
            if pb_city: entity_pages.append(pb_city)

    # ==========================================
    # 2. لایه ۱: برند (فقط با کلمه هاردکد شده "ریموت")
    # ==========================================
    for brand in brands:
        pb = upsert_pagebrief(
            project=project, keyword=brand_hub_kw, entity=brand, 
            page_level=1, page_type=PageBrief.PageType.PILLAR, 
            url_path=pillar_url(brand, brand_hub_kw, is_master=True), parent_page=None,
            target_word_count=2500
        )
        if pb: entity_pages.append(pb)

    # ==========================================
    # 3. لایه ۲: مدل‌ها (پیلارها بر اساس کلمات کلیدی)
    # ==========================================
    for model in models:
        parent_brand_pb = PageBrief.objects.filter(project=project, entity=model.parent, keyword=brand_hub_kw, page_level=1).first()
        
        for p_kw in layer2_pillars_kws:
            is_master = (p_kw.text == "ریموت")
            pb = upsert_pagebrief(
                project=project, keyword=p_kw, entity=model, 
                page_level=2, page_type=PageBrief.PageType.PILLAR, 
                url_path=pillar_url(model, p_kw, is_master=is_master), parent_page=parent_brand_pb,
                target_word_count=2500
            )
            if pb: entity_pages.append(pb)

    # ==========================================
    # 4. لایه ۳: ساخت کلاسترها و تزریق کنونیکال
    # ==========================================
    for kw in cluster_keywords:
        if kw.text in root_texts or kw.text == "ریموت":
            continue

        intent_code = kw.intent.code.lower() if kw.intent else ""
        
        if intent_code == "informational" or not kw.service_id:
            url_path = f"/mag/{slugify(kw.text.split(',')[0], allow_unicode=True)}/"
            pb = upsert_pagebrief(
                project=project, keyword=kw, entity=None, page_level=0, page_type=PageBrief.PageType.EDUCATIONAL, 
                url_path=url_path, parent_page=None, target_word_count=3000
            )
            if pb: keyword_pages.append(pb)
            continue

        for model in models:
            if kw.parent_keyword_id:
                parent_model_pb = PageBrief.objects.filter(project=project, entity=model, keyword_id=kw.parent_keyword_id, page_level=2).first()
            else:
                parent_model_pb = PageBrief.objects.filter(project=project, entity=model, keyword__text="ریموت", page_level=2).first()

            canonical_url = f"{project.base_domain.rstrip('/')}{parent_model_pb.url_path}" if parent_model_pb else ""
            is_parent_master = (parent_model_pb and parent_model_pb.keyword.text == "ریموت")
            
            url_path = cluster_url(model, kw, parent_keyword=kw.parent_keyword, is_parent_master=is_parent_master)
            
            pb = upsert_pagebrief(
                project=project, keyword=kw, entity=model,
                page_level=3, page_type=PageBrief.PageType.CLUSTER,
                url_path=url_path, parent_page=parent_model_pb,
                canonical_url=canonical_url,
                target_word_count=random.randint(1500, 2000)
            )
            if pb: keyword_pages.append(pb)

    # فاز خودترمیمی تصحیح والدین ساختارها
    all_pages_qs = PageBrief.objects.filter(project=project, is_active=True).select_related('keyword')
    for p in all_pages_qs:
        if p.locked or p.page_level != 3 or not p.entity_id:
            continue
            
        correct_parent = None
        if p.keyword.parent_keyword_id:
            correct_parent = next((v for v in all_pages_qs if v.page_level == 2 and v.entity_id == p.entity_id and v.keyword_id == p.keyword.parent_keyword_id), None)
        else:
            correct_parent = next((v for v in all_pages_qs if v.page_level == 2 and v.entity_id == p.entity_id and v.keyword.text == "ریموت"), None)

        if correct_parent and p.parent_page_id != correct_parent.id:
            p.parent_page = correct_parent
            p.save()

    if rebuild_links:
        build_links(project)

    return {
        "root_pages": root_pages,
        "entity_pages": entity_pages,
        "keyword_pages": keyword_pages,
    }
