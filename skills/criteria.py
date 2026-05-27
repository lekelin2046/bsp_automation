"""
评级准入门槛判定 Skill
判断财报数据是否满足评级要求，不满足则生成作废原因
"""
from typing import Tuple

VOID_REASONS = {
    'no_financial': '无法获取完整的近三年财务数据，不满足评级准入条件',
    'negative_profit': '企业连续亏损（净利润为负），不满足曼德评级准入条件',
    'high_debt': '资产负债率超过80%，偿债风险较高，不满足曼德评级准入条件',
    'pdf_format_error': '财报PDF格式异常，无法提取有效财务数据，已退回',
}


def check_eligibility(bs_data: dict, pl_data: dict) -> Tuple[bool, str]:
    """
    检查企业是否满足评级门槛
    返回: (通过: bool, 原因: str)
    """
    reasons = []
    
    # 1. 数据完整性检查
    years_bs = sum(1 for y in [2023, 2024, 2025] if y in bs_data and len(bs_data[y]) > 3)
    years_pl = sum(1 for y in [2023, 2024, 2025] if y in pl_data and len(pl_data[y]) > 3)
    if years_bs == 0 and years_pl == 0:
        return False, VOID_REASONS['pdf_format_error']
    if years_bs < 1 or years_pl < 1:
        return False, VOID_REASONS['no_financial']
    
    # 2. 净利润检查（任一亏损则退回）
    for y in [2023, 2024, 2025]:
        if y in pl_data:
            for key in ['四、净利润（净亏损以"-"号填列）', '四、净利润', '净利润']:
                if key in pl_data[y] and pl_data[y][key] < 0:
                    return False, VOID_REASONS['negative_profit']
    
    # 3. 资产负债率检查
    for y in [2023, 2024, 2025]:
        if y in bs_data:
            total_assets = bs_data[y].get('资产总计', 0) or bs_data[y].get('负债和股东权益总计', 0)
            total_liab = bs_data[y].get('负债合计', 0)
            if total_assets and total_assets > 0:
                ratio = total_liab / total_assets * 100
                if ratio > 80:
                    reasons.append(f'{y}年资产负债率{ratio:.0f}%')
    
    if reasons:
        return False, VOID_REASONS['high_debt'] + f"（{'; '.join(reasons)}）"
    
    return True, ""
