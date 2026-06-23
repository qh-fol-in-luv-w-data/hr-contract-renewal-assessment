"""API endpoints: OCR batch phiếu đánh giá nhân sự + AI overview + export Excel."""
import json
import frappe
from cnb_2as.services.bao_cao_service import (
    ocr_batch, map_phieu_list, ai_overviews_batch,
    build_excel, parse_hr_files, build_hr_template_excel, _norm_name,
)


@frappe.whitelist()
def ocr_batch_upload():
    """
    POST multipart/form-data với nhiều file PDF.
    Trả JSON: {"ok": True, "persons": [...], "count": N}
    """
    import traceback as _tb
    try:
        files_bytes = []
        hr_files_bytes = []
        for key, fobj in frappe.request.files.items():
            if not key.startswith("file"):
                continue
            fname = fobj.filename or key
            fbytes = fobj.read()
            if not fbytes:
                continue
            if fname.lower().endswith((".xlsx", ".xls")):
                hr_files_bytes.append(fbytes)
            else:
                files_bytes.append((fname, fbytes))

        if not files_bytes:
            frappe.throw("Không có file PDF nào được upload.", frappe.ValidationError)

        raw_results = ocr_batch(files_bytes)
        persons = map_phieu_list(raw_results)

        # Attach HR data nếu có file(s) Excel
        if hr_files_bytes:
            hr_data = parse_hr_files(hr_files_bytes)
            for p in persons:
                nkey = _norm_name(p.get("ho_ten") or p.get("ten") or "")
                p["hr_data"] = hr_data.get(nkey, {})

        return {"ok": True, "persons": persons, "count": len(persons)}
    except frappe.ValidationError:
        raise
    except Exception as _e:
        err_msg = str(_e)
        if "insufficient_quota" in err_msg:
            return {"ok": False, "error": "OpenAI API hết quota. Kiểm tra billing tại platform.openai.com"}
        if "invalid_api_key" in err_msg or "Incorrect API key" in err_msg:
            return {"ok": False, "error": "OpenAI API key không hợp lệ. Kiểm tra site_config.json"}
        err = _tb.format_exc()
        return {"ok": False, "error": err[-1500:]}


@frappe.whitelist()
def analyze_ai():
    """
    POST form-data: data=<JSON string của persons list>
    Chạy AI overview song song, trả JSON overviews list.
    """
    data_str = frappe.form_dict.get("data")
    if not data_str:
        frappe.throw("Thiếu dữ liệu persons.", frappe.ValidationError)

    persons = json.loads(data_str)
    overviews = ai_overviews_batch(persons)
    return {"ok": True, "overviews": overviews}


@frappe.whitelist()
def export_excel():
    """
    POST form-data:
      data=<JSON persons list>
      overviews=<JSON overviews list, optional — pre-computed từ analyze_ai>
    Trả file Excel download.
    """
    data_str = frappe.form_dict.get("data")
    if not data_str:
        frappe.throw("Thiếu dữ liệu persons.", frappe.ValidationError)

    persons = json.loads(data_str)

    overviews_str = frappe.form_dict.get("overviews")
    overviews = json.loads(overviews_str) if overviews_str else None

    phong_ban = frappe.form_dict.get("phong_ban", "")

    hr_data = None
    hr_files_bytes = []
    for key, fobj in frappe.request.files.items():
        if key.startswith("file_hr") or key == "hr_file":
            fb = fobj.read()
            if fb:
                hr_files_bytes.append(fb)
    if hr_files_bytes:
        hr_data = parse_hr_files(hr_files_bytes)

    excel_bytes = build_excel(persons, overviews, phong_ban=phong_ban, hr_data=hr_data)

    frappe.response.filename = "bao_cao_danh_gia_nhan_su.xlsx"
    frappe.response.filecontent = excel_bytes
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"


@frappe.whitelist()
def download_hr_template():
    """
    POST form-data: data=<JSON persons list> (tùy chọn)
    Trả file Excel template pre-filled tên từ danh sách persons.
    Nếu không có data → template rỗng.
    """
    persons = []
    data_str = frappe.form_dict.get("data")
    if data_str:
        try:
            persons = json.loads(data_str)
        except Exception:
            pass
    excel_bytes = build_hr_template_excel(persons)
    frappe.response.filename = "template_hr_data.xlsx"
    frappe.response.filecontent = excel_bytes
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"
