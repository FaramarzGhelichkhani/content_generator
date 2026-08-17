// باز کردن قفل کامل فیلدهای رنک مث برای خواندن و نوشتن در REST API
add_action( 'rest_api_init', function () {
    $meta_fields = array('rank_math_title', 'rank_math_description', 'rank_math_canonical_url', 'rank_math_focus_keyword');
    
    foreach ($meta_fields as $field) {
        register_post_meta( 'post', $field, array(
            'show_in_rest' => true,
            'single'       => true,
            'type'         => 'string',
            'auth_callback'=> function() { 
                return current_user_can('edit_posts'); 
            }
        ));
    }
});

// همگام‌سازی نهایی فیلدهای دریافتی API با سشن اصلی دیتابیس رنک مث
add_action('rest_insert_post', function($post, $request, $creating) {
    $meta = $request->get_param('meta');
    if (!empty($meta)) {
        if (isset($meta['rank_math_title'])) {
            update_post_meta($post->ID, 'rank_math_title', sanitize_text_field($meta['rank_math_title']));
        }
        if (isset($meta['rank_math_description'])) {
            update_post_meta($post->ID, 'rank_math_description', sanitize_text_field($meta['rank_math_description']));
        }
        if (isset($meta['rank_math_canonical_url'])) {
            update_post_meta($post->ID, 'rank_math_canonical_url', esc_url_raw($meta['rank_math_canonical_url']));
        }
        if (isset($meta['rank_math_focus_keyword'])) {
            update_post_meta($post->ID, 'rank_math_focus_keyword', sanitize_text_field($meta['rank_math_focus_keyword']));
        }
    }
}, 10, 3);

// اضافه کردن فیلد سفارشی آدرس دلخواه به REST API
add_action( 'rest_api_init', function () {
    register_post_meta( 'post', 'custom_permalink', array(
        'show_in_rest' => true,
        'single'       => true,
        'type'         => 'string',
        'auth_callback'=> function() { return current_user_can('edit_posts'); }
    ));
});

// همگام‌سازی نهایی آدرس ارسالی از پایتون
add_action('rest_insert_post', function($post, $request, $creating) {
    $meta = $request->get_param('meta');
    if (!empty($meta) && isset($meta['custom_permalink'])) {
        update_post_meta($post->ID, 'custom_permalink', sanitize_text_field($meta['custom_permalink']));
    }
}, 10, 3);

// فورس کردن آپدیت جدول مسیرها (Rewrite Rules) بعد از ارسال از پایتون
add_action('rest_after_insert_post', function($post, $request, $creating) {
    $meta = $request->get_param('meta');
    if (isset($meta['custom_permalink'])) {
        // آپدیت کش مسیرهای افزونه کاستوم پرمالینک
        if (function_exists('custom_permalinks_flush_rewrite_rules')) {
            custom_permalinks_flush_rewrite_rules();
        }
    }
}, 10, 3);


// استخراج بلوک‌های متنی بر اساس شماره (ایندکس)
add_shortcode('ai_block', function($atts) {
    $atts = shortcode_atts(array('index' => 0), $atts);
    global $post;
    if (!$post) return '';

    // پارس کردن کامنت‌های گوتنبرگ
    $blocks = parse_blocks($post->post_content);
    
    // فیلتر کردن بلوک‌های خالی (فاصله‌ها و اینترهای گوتنبرگ)
    $valid_blocks = array_values(array_filter($blocks, function($block) {
        return !empty(trim($block['innerHTML']));
    }));

    $idx = intval($atts['index']);
    if (isset($valid_blocks[$idx])) {
        return render_block($valid_blocks[$idx]);
    }
    return '';
});

// استخراج بلوک اختصاصی تصویر موجودیت (با کلاس wp-seo-entity-image)
add_shortcode('ai_image_block', function() {
    global $post;
    if (!$post) return '';
    $blocks = parse_blocks($post->post_content);
    foreach ($blocks as $block) {
        if (isset($block['attrs']['className']) && strpos($block['attrs']['className'], 'wp-seo-entity-image') !== false) {
            return render_block($block);
        }
    }
    return '';
});

// استخراج کارت اختصاصی سوالات متداول (با کلاس wp-seo-faq-card)
add_shortcode('ai_faq_block', function() {
    global $post;
    if (!$post) return '';
    $blocks = parse_blocks($post->post_content);
    foreach ($blocks as $block) {
        if (isset($block['attrs']['className']) && strpos($block['attrs']['className'], 'wp-seo-faq-card') !== false) {
            return render_block($block);
        }
    }
    return '';
});
