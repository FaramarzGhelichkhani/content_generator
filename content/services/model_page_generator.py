# content/services/model_page_generator.py
import hashlib
from django.db import transaction
from django.utils.text import slugify
from core.models import Project
from taxonomy.models import ServiceType, TaxonomyNode, Location
from content.models import Keyword, PageBrief, PageContent, InternalLink

class ModelPageGeneratorService:
    def __init__(self, project_id=1):
        self.project = Project.objects.get(id=project_id)
        
        # بارگذاری سرویس‌ها
        self.create_service = ServiceType.objects.get(project=self.project, code=ServiceType.Code.CREATE_REMOTE)
        self.shop_service = ServiceType.objects.get(project=self.project, code=ServiceType.Code.SELL_REMOTE)
        self.copy_service = ServiceType.objects.get(project=self.project, code=ServiceType.Code.COPY_REMOTE)
        self.repair_service = ServiceType.objects.get(project=self.project, code=ServiceType.Code.REPAIR_REMOTE)
        
        # بارگذاری کلیدواژه‌های اصلی
        self.create_pillar_kw = Keyword.objects.get(project=self.project, text=self.create_service.root_keyword, is_pillar=True)
        self.shop_pillar_kw = Keyword.objects.get(project=self.project, text=self.shop_service.root_keyword, is_pillar=True)
        
        # بارگذاری کلاسترهای هر نیت
        self.create_clusters_kw = Keyword.objects.filter(parent_keyword=self.create_pillar_kw, is_pillar=False)
        self.shop_clusters_kw = Keyword.objects.filter(parent_keyword=self.shop_pillar_kw, is_pillar=False)
        
        # بارگذاری شهرها
        self.cities = Location.objects.filter(project=self.project, parent__isnull=False)

    def _get_dynamic_anchor(self, seed_text, model_name, brand_name, is_shop=False):
        """
        تولید انکرتکست‌های متنوع برای جلوگیری از ایجاد Footprint در سئو.
        از هش کردن seed_text (نام کلاستر) استفاده می‌کنیم تا خروجی همیشه برای یک کلاستر ثابت بماند اما بین کلاسترها متنوع باشد.
        """
        if is_shop:
            anchors = [
                f"ریموت {model_name}"
                f"خرید ریموت فابریک {model_name}",
                f"قیمت ریموت اصلی {model_name}",
                f"خرید کیلس {brand_name} {model_name}",
                f"فروشگاه ریموت {model_name}",
                f"سفارش ریموت اورجینال {model_name}",
            ]
        else:
            anchors = [
                f" ساخت ریموت {model_name}",
                f"مرکز ساخت ریموت {model_name}",
                f"خدمات تخصصی کیلس {model_name}",
                f"پروگرام ریموت {brand_name} {model_name}",
                f"ریموت‌سازی {model_name}",
                f"کددهی سوئیچ {model_name}",
                f"مرکز خدمات کیلس {brand_name} {model_name}"
            ]
        
        # استفاده از MD5 برای تولید یک ایندکس یکتا اما ثابت بر اساس متن کلاستر
        hash_val = int(hashlib.md5(seed_text.encode('utf-8')).hexdigest(), 16)
        return anchors[hash_val % len(anchors)]

    @transaction.atomic
    def process_models(self, model_nodes):
        stats = {"pages_created": 0, "pages_updated": 0, "links_created": 0}
        brand_pillars = {} # برای ذخیره پیلارهای ساخته شده به تفکیک برند جهت لینک‌سازی افقی

        for model_node in model_nodes:
            if model_node.kind != TaxonomyNode.Kind.MODEL or not model_node.parent:
                continue
                
            brand_node = model_node.parent
            brand_slug = brand_node.slug
            model_slug = model_node.slug

            if brand_node.id not in brand_pillars:
                brand_pillars[brand_node.id] = {"service_pillars": [], "shop_pillars": []}

            # گرفتن رفرنس صفحات برند (لایه ۲) جهت لینک‌دهی عمودی
            brand_service_brief = PageBrief.objects.filter(
                project=self.project, entity=brand_node, page_level=2, service_type=self.create_service
            ).first()
            
            # -----------------------------------------------------------------
            # ۱. ساخت صفحات پیلار مدل (لایه ۳)
            # -----------------------------------------------------------------
            # الف) پیلار خدمات
            service_pillar_url = f"/{brand_slug}/{model_slug}/{self.create_service.slug}/"
            service_pillar_brief, created = PageBrief.objects.update_or_create(
                project=self.project, url_path=service_pillar_url,
                defaults={
                    "service_type": self.create_service, "entity": model_node, "location": None,
                    "page_level": 3, "keyword": self.create_pillar_kw, "page_type": PageBrief.PageType.PILLAR,
                    "target_word_count": 2200,
                }
            )
            PageContent.objects.get_or_create(page_brief=service_pillar_brief)
            if created: stats["pages_created"] += 1 
            else: stats["pages_updated"] += 1
            brand_pillars[brand_node.id]["service_pillars"].append(service_pillar_brief)

            # لینک عمودی از پیلار مدل به پیلار برند (لایه ۳ به لایه ۲)
            if brand_service_brief:
                _, l_brand = InternalLink.objects.get_or_create(
                    source_page=service_pillar_brief, target_page=brand_service_brief,
                    defaults={"anchor_text": f"مرکز خدمات ریموت {brand_node.name}", "relation_type": InternalLink.RelationType.VERTICAL}
                )
                if l_brand: stats["links_created"] += 1
                
            # ب) پیلار فروشگاه
            shop_pillar_url = f"/{brand_slug}/{model_slug}/"
            shop_pillar_brief, created = PageBrief.objects.update_or_create(
                project=self.project, url_path=shop_pillar_url,
                defaults={
                    "service_type": self.shop_service, "entity": model_node, "location": None,
                    "page_level": 3, "keyword": self.shop_pillar_kw, "page_type": PageBrief.PageType.PILLAR,
                    "target_word_count": 2000,
                }
            )
            PageContent.objects.get_or_create(page_brief=shop_pillar_brief)
            if created: stats["pages_created"] += 1 
            else: stats["pages_updated"] += 1
            brand_pillars[brand_node.id]["shop_pillars"].append(shop_pillar_brief)

            # لینک عمودی از پیلار مدل به پیلار برند (لایه ۳ به لایه ۲)
            if brand_service_brief:
                _, l_brand = InternalLink.objects.get_or_create(
                    source_page=shop_pillar_brief, target_page=brand_service_brief,
                    defaults={"anchor_text": f"مرکز خدمات ریموت {brand_node.name}", "relation_type": InternalLink.RelationType.VERTICAL}
                )
                if l_brand: stats["links_created"] += 1
                # لینک از برند به صفحه فروشگاه
                _, l_brand = InternalLink.objects.get_or_create(
                            source_page=brand_service_brief, target_page=shop_pillar_brief,
                                defaults={"anchor_text": f" ریموت {model_node.name}", "relation_type": InternalLink.RelationType.VERTICAL}
                                        )
                if l_brand: stats["links_created"] += 1    

            # لینک افقی بین دو پیلار یک مدل (خدمات <--> فروشگاه)
            _, l1 = InternalLink.objects.get_or_create(
                source_page=service_pillar_brief, target_page=shop_pillar_brief,
                defaults={"anchor_text": f"خرید ریموت {brand_node.name} {model_node.name}", "relation_type": InternalLink.RelationType.HORIZONTAL}
            )
            _, l2 = InternalLink.objects.get_or_create(
                source_page=shop_pillar_brief, target_page=service_pillar_brief,
                defaults={"anchor_text": f"خدمات ساخت ریموت {model_node.name}", "relation_type": InternalLink.RelationType.HORIZONTAL}
            )
            if l1: stats["links_created"] += 1
            if l2: stats["links_created"] += 1

            # -----------------------------------------------------------------
            # ۲. ساخت صفحات کلاستر مدل (لایه ۴)
            # -----------------------------------------------------------------
            
            # الف) کلاسترهای خدماتی
            for kw in self.create_clusters_kw:
                kw_slug = slugify(kw.text, allow_unicode=True)
                cluster_url = f"/{brand_slug}/{model_slug}/{kw_slug}/"

                service_= self.create_service
                if kw.text == self.copy_service.root_keyword:
                    service_=self.copy_service
                if kw.text == self.repair_service.root_keyword:
                    service_=self.repair_service    

                cluster_brief, created = PageBrief.objects.update_or_create(
                    project=self.project, url_path=cluster_url,
                    defaults={
                        "service_type":service_ , "entity": model_node, "location": None,
                        "page_level": 4, "keyword": kw, "page_type": PageBrief.PageType.CLUSTER, "target_word_count": 1500,
                    }
                )
                PageContent.objects.get_or_create(page_brief=cluster_brief)
                if created: stats["pages_created"] += 1

                # لینک رو به بالا از کلاستر به پیلار خدمات با انکرتکست متنوع
                dynamic_anchor = self._get_dynamic_anchor(kw.text, model_node.name, brand_node.name, is_shop=False)
                _, lc = InternalLink.objects.get_or_create(
                    source_page=cluster_brief, target_page=service_pillar_brief,
                    defaults={"anchor_text": dynamic_anchor, "relation_type": InternalLink.RelationType.VERTICAL}
                )
                if lc: stats["links_created"] += 1

            # ب) کلاسترهای شهر برای خدمات (لایه ۴)
            for city in self.cities:
                city_cluster_url = f"/{city.slug}/{brand_slug}/{model_slug}/{self.create_service.slug}/"
                city_brief, created = PageBrief.objects.update_or_create(
                    project=self.project, url_path=city_cluster_url,
                    defaults={
                        "service_type": self.create_service, "entity": model_node, "location": city,
                        "page_level": 4, "keyword": self.create_pillar_kw, "page_type": PageBrief.PageType.CLUSTER, "target_word_count": 2000,
                    }
                )
                PageContent.objects.get_or_create(page_brief=city_brief)
                if created: stats["pages_created"] += 1

                # لینک رو به بالا از کلاستر شهر به پیلار خدمات
                dynamic_anchor = self._get_dynamic_anchor(city.name, model_node.name, brand_node.name, is_shop=False)
                _, lc = InternalLink.objects.get_or_create(
                    source_page=city_brief, target_page=service_pillar_brief,
                    defaults={"anchor_text": dynamic_anchor, "relation_type": InternalLink.RelationType.VERTICAL}
                )
                if lc: stats["links_created"] += 1

            # ج) کلاسترهای فروشگاهی
            for kw in self.shop_clusters_kw:
                kw_slug = slugify(kw.text, allow_unicode=True)
                shop_cluster_url = f"/{brand_slug}/{model_slug}/{kw_slug}/"
                s_cluster_brief, created = PageBrief.objects.update_or_create(
                    project=self.project, url_path=shop_cluster_url,
                    defaults={
                        "service_type": self.shop_service, "entity": model_node, "location": None,
                        "page_level": 4, "keyword": kw, "page_type": PageBrief.PageType.CLUSTER, "target_word_count": 1500,
                    }
                )
                PageContent.objects.get_or_create(page_brief=s_cluster_brief)
                if created: stats["pages_created"] += 1

                # لینک رو به بالا از کلاستر فروشگاهی به پیلار فروشگاه
                dynamic_anchor = self._get_dynamic_anchor(kw.text, model_node.name, brand_node.name, is_shop=True)
                _, lc = InternalLink.objects.get_or_create(
                    source_page=s_cluster_brief, target_page=shop_pillar_brief,
                    defaults={"anchor_text": dynamic_anchor, "relation_type": InternalLink.RelationType.VERTICAL}
                )
                if lc: stats["links_created"] += 1

        # -----------------------------------------------------------------
        # ۳. لینک‌دهی افقی بین مدل‌های یک برند (مدل به مدل)
        # -----------------------------------------------------------------
        for brand_id, pillars in brand_pillars.items():
            # لینک افقی بین پیلارهای خدماتی مدل‌ها
            srv_pillars = pillars["service_pillars"]
            for source in srv_pillars:
                for target in srv_pillars:
                    if source != target:
                        _, created = InternalLink.objects.get_or_create(
                            source_page=source, target_page=target,
                            defaults={"anchor_text": f"ساخت ریموت {target.entity.name}", "relation_type": InternalLink.RelationType.HORIZONTAL}
                        )
                        if created: stats["links_created"] += 1

            # لینک افقی بین پیلارهای فروشگاهی مدل‌ها
            shp_pillars = pillars["shop_pillars"]
            for source in shp_pillars:
                for target in shp_pillars:
                    if source != target:
                        _, created = InternalLink.objects.get_or_create(
                            source_page=source, target_page=target,
                            defaults={"anchor_text": f"ریموت {target.entity.name}", "relation_type": InternalLink.RelationType.HORIZONTAL}
                        )
                        if created: stats["links_created"] += 1

        return stats
    