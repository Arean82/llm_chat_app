// i18n.js - Frontend Localization Module

let translations = {};
let currentLocale = 'en';

/**
 * Initializes the localization engine by fetching the target locale file.
 */
export async function initI18n(locale = 'en') {
    currentLocale = locale;
    try {
        const response = await fetch(`/static/locales/${locale}.json`);
        if (!response.ok) throw new Error(`Could not load locale: ${locale}`);
        translations = await response.json();
        
        // Apply translations to the DOM
        applyTranslations();
    } catch (error) {
        console.error("[i18n] Failed to initialize localization:", error);
    }
}

/**
 * Retrieves a translated string based on dot-notation key (e.g. "auth.step_1_title").
 */
export function t(key) {
    const keys = key.split('.');
    let result = translations;
    for (const k of keys) {
        if (result === undefined || result === null) return key;
        result = result[k];
    }
    return result !== undefined ? result : key;
}

/**
 * Scans the DOM for elements with data-i18n attributes and updates them.
 */
export function applyTranslations() {
    // 1. Text content replacement (preserves child HTML if we only want to replace specific text nodes, 
    // but for simplicity we replace innerHTML or textContent depending on the use case.
    // To support icons inside buttons, we'll use a specialized attribute data-i18n-text
    // or just replace the text node.

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const translated = t(key);
        
        if (translated !== key) {
            // Check if we need to preserve an icon
            const icon = el.querySelector('i');
            if (icon) {
                // If there's an icon, we rebuild the content
                // Assumes format: <i class="..."></i> Text
                const iconOuter = icon.outerHTML;
                
                // Keep spans if they exist (like idle-text / loading-text wrappers)
                if (el.children.length > 1 || el.querySelector('span')) {
                    // Complex element, skip direct replacement or handle carefully
                    // (We will handle these by putting data-i18n directly on the text spans in HTML)
                    el.innerHTML = translated;
                } else {
                    el.innerHTML = `${iconOuter} ${translated}`;
                }
            } else {
                el.innerHTML = translated;
            }
        }
    });

    // 2. Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        const translated = t(key);
        if (translated !== key) {
            el.placeholder = translated;
        }
    });

    // 3. Titles/Tooltips
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        const translated = t(key);
        if (translated !== key) {
            el.title = translated;
        }
    });
}
