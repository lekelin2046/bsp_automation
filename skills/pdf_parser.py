"""
PDF 财报解析 Skill
双引擎策略：MinerU(免费) 预检 → TextIn(收费) 精准提取
"""
import json, os, re, subprocess, time
from pathlib import Path
from typing import Dict, List

# ── 配置 ──
SCRIPT_DIR = Path(__file__).parent.parent
TEXTIN_SCRIPT = Path.home() / ".openclaw" / "workspace" / "skills" / "textin-parse" / "scripts" / "parse.py"
MINERU_CONFIG = Path.home() / ".openclaw" / "mineru-config.json"

def parse_val(v):
    if not v: return 0
    v = v.replace(',','').replace('元','').strip()
    try: return float(v) if v else 0
    except: return 0

# ═══════════════════════════════════════════
#  MinerU 引擎（免费，每日1000页）
# ═══════════════════════════════════════════

def mineru_preview(pdf_path: str) -> dict:
    """用 MinerU 快速预览 PDF，判断是否包含有效财报"""
    if not MINERU_CONFIG.exists():
        return {"valid": False, "error": "MinerU 未配置"}
    try:
        with open(MINERU_CONFIG) as f:
            token = json.load(f)['token']
    except:
        return {"valid": False, "error": "MinerU token 读取失败"}
    
    import requests
    with open(pdf_path, 'rb') as f:
        r = requests.post(
            'https://mineru.net/api/v1/agent/parse/file',
            headers={'Authorization': f'Bearer {token}'},
            files={'file': (os.path.basename(pdf_path), f, 'application/pdf')},
            data={'file_name': os.path.basename(pdf_path)},
            timeout=30
        )
    if r.status_code != 200:
        return {"valid": False, "error": f"MinerU API 返回 {r.status_code}"}
    
    data = r.json()
    # MinerU 返回中的验证逻辑（TODO: 根据实际返回调整）
    return {"valid": True, "raw": data}


# ═══════════════════════════════════════════
#  TextIn 引擎（精准OCR，按量计费）
# ═══════════════════════════════════════════

def textin_extract(pdf_path: str) -> str:
    """用 TextIn 解析 PDF 为 Markdown"""
    result = subprocess.run(
        f'python3 "{TEXTIN_SCRIPT}" parse "{pdf_path}"',
        shell=True, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"TextIn 解析失败: {result.stderr[:200]}")
    return result.stdout


# ═══════════════════════════════════════════
#  表格提取
# ═══════════════════════════════════════════

def _extract_table(text: str, table_type: str) -> dict:
    """从 Markdown 文本中提取财务表格数据"""
    import re
    
    idx = text.find(f'**{table_type}**')
    if idx == -1: return {}
    
    section = text[idx:]
    m = re.search(r'<table[^>]*>', section)
    if not m: return {}
    ts = m.end() - len(m.group())
    te = section.find('</table>', ts)
    if te == -1: return {}
    html = section[ts:te+8]
    
    is_bs = '负债和所有者权益' in html
    rows = re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL)
    
    SKIP = {'资产','项目','行次','流动资产：','非流动资产：',
            '流动负债：','非流动负债：','所有者权益（或股东权益）',
            '其中：原材料','其中：','在产品','库存商品','周转材料',
            '消费税','营业税','城市维护建设税','资源税','土地增值税',
            '城镇土地使用税、房产税、车船税、印花税',
            '教育费附加、矿产资源补偿费、排污费',
            '其中：商品维修费','广告费和业务宣传费',
            '其中：开办费','业务招待费','研究费用',
            '其中：利息费用（收入以"-"号填列）',
            '其中：利息费用（收入以"－"号填列）',
            '其中：政府补助','其中：坏账损失',
            '无法收回的长期债券投资损失','无法收回的长期股权投资损失',
            '自然灾害等不可抗力因素造成的损失','税收滞纳金',
            '固定资产原价','减：累计折旧'}
    
    result = {}
    for row in rows:
        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL)
        cells = [c.strip().replace('\n','').replace('\r','') for c in cells]
        if not cells: continue
        first = cells[0]
        if first in SKIP: continue
        
        if len(cells) >= 8 and is_bs:
            if cells[0]: result[cells[0]] = parse_val(cells[2])
            if len(cells) > 4 and cells[4] and '债和所有者权益' not in cells[4]:
                result[cells[4]] = parse_val(cells[6])
        elif len(cells) >= 4 and not is_bs:
            result[cells[0]] = parse_val(cells[2])
    
    return result


def parse_financial_data(pdf_files: List[Path]) -> tuple:
    """
    解析多个PDF财报文件
    返回: (bs_data: dict, pl_data: dict)
    bs_data = {year: {item: value, ...}}
    pl_data = {year: {item: value, ...}}
    """
    bs_data, pl_data = {}, {}
    
    # 先验证文件完整性
    valid_years = 0
    for pdf in pdf_files:
        year_match = re.search(r'(\d{4})', pdf.name)
        if year_match:
            valid_years += 1
    
    if valid_years < 2:
        return None, "未找到完整的3年财务数据PDF"
    
    # 逐个解析
    for pdf_path in pdf_files:
        year_match = re.search(r'(\d{4})', pdf_path.name)
        if not year_match: continue
        year = int(year_match.group(1))
        
        print(f"   解析 {pdf_path.name} ({year})...")
        text = textin_extract(str(pdf_path))
        
        bs_data[year] = _extract_table(text, '资产负债表')
        pl_data[year] = _extract_table(text, '利润表')
    
    return (bs_data, pl_data), None
