app_name = "cnb_2as"
app_title = "CNB 2AS – AI Đánh Giá Nhân Sự"
app_publisher = "CT Group"
app_description = "Hệ thống AI đánh giá thử việc và tái ký hợp đồng"
app_email = "dev@ctgroup.vn"
app_license = "mit"
app_icon = "octicon octicon-pulse"
app_color = "#6366f1"

# Fixtures
# fixtures = []


# SPA Routing
website_route_rules = [
    {"from_route": "/aicenter/2as-employee-assessment/<path:app_path>", "to_route": "cnb_2as_spa"},
    {"from_route": "/aicenter/2as-employee-assessment", "to_route": "cnb_2as_spa"}
]
