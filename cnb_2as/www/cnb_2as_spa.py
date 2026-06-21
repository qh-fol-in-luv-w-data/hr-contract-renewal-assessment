import frappe
import os
import re

no_cache = 1

def get_context(context):
    context.no_header = 1
    context.no_sidebar = 1
    context.no_breadcrumbs = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    app_path = frappe.get_app_path("cnb_2as", "public", "frontend", "index.html")
    if os.path.exists(app_path):
        with open(app_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # Extract content from <body>...</body>, or use the whole file
        body_match = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL)
        body_content = body_match.group(1).strip() if body_match else raw

        # Extract <script> and <link> tags from <head> so they're not lost
        head_match = re.search(r'<head[^>]*>(.*?)</head>', raw, re.DOTALL)
        head_tags = ""
        if head_match:
            head_html = head_match.group(1)
            scripts = re.findall(r'<script[^>]*>.*?</script>', head_html, re.DOTALL)
            links = re.findall(r'<link[^>]*/?>', head_html)
            # Only keep asset links (not preconnect, etc.)
            asset_links = [l for l in links if 'stylesheet' in l or '/assets/' in l]
            head_tags = "\n".join(asset_links + scripts)

        context.vue_html = f"{head_tags}\n{body_content}"
    else:
        context.vue_html = "<div>Please run npm run build in frontend directory of 2as-employee-assessment.</div>"
    return context
