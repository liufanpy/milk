"""通用 CSV 导入解析器"""
import csv
import io
from typing import Callable


def parse_csv(file_content: bytes, validate_row: Callable, allowed_headers: list[str]) -> dict:
    """解析 CSV 文件，对每行调用 validate_row 校验，返回预览格式"""
    # 编码检测
    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_content.decode("gbk")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {"headers": [], "rows": [], "summary": {"total": 0, "ok": 0, "error": 0}}

    # 过滤空表头
    headers = [h.strip() for h in reader.fieldnames if h and h.strip()]

    rows = []
    ok = 0
    error = 0
    for idx, raw_row in enumerate(reader):
        # 跳过全空行
        row = {k.strip(): (v or "").strip() for k, v in raw_row.items() if k and k.strip()}
        if not any(v for v in row.values()):
            continue

        validation = validate_row(row)
        if validation is True:
            rows.append({"index": idx, "data": row, "status": "ok", "msg": ""})
            ok += 1
        else:
            rows.append({"index": idx, "data": row, "status": "error", "msg": validation})
            error += 1

    return {
        "headers": headers,
        "rows": rows,
        "summary": {"total": ok + error, "ok": ok, "error": error},
    }
