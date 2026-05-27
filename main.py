#!/usr/bin/env python3
"""
BSP 曼德评级自动化系统
========================
交互式控制台入口

用法:
  python3 main.py                          # 交互式菜单
  python3 main.py --auto                   # 自动处理全部待评级
  python3 main.py --customer "企业名"       # 处理指定企业
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright

from config import WORK_DIR, TEMPLATE_PATH
from browser import ensure_chrome
from skills.pdf_parser import parse_financial_data
from skills.template_filler import fill_template
from skills.criteria import check_eligibility, VOID_REASONS
from skills.bsp_client import (
    login, get_customer_list, click_rate, download_pdfs,
    upload_financial, click_rate_button, click_back,
    click_push, void_customer
)

log = lambda msg: print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ── 数据模板 ──
TEMPLATE_PATH  # loaded from config

# ── 保证模板文件存在 ──
if not TEMPLATE_PATH.exists():
    # 从 workspace 复制
    src = Path.home() / ".openclaw" / "workspace" / "模板.xlsx"
    if src.exists():
        TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(src), str(TEMPLATE_PATH))
        log(f"✅ 模板已复制到 {TEMPLATE_PATH}")
    else:
        log(f"❌ 模板文件不存在: {src}")


def process_single(page, customer_name, auto_confirm=False):
    """处理单个客户全流程"""
    log(f"\n{'='*50}")
    log(f"🎯 处理: {customer_name}")
    log(f"{'='*50}")
    
    # 1. 点评级 → 进评分页
    if not click_rate(page, customer_name):
        return False
    
    # 2. 打包下载PDF
    pdf_dir = download_pdfs(page, customer_name, "")
    pdf_files = sorted(Path(pdf_dir).glob("*.pdf"))
    log(f"   下载 {len(pdf_files)} 个PDF")
    
    if not pdf_files:
        log("   ❌ 未下载到PDF文件")
        void_customer(page, customer_name, VOID_REASONS['no_financial'])
        return False
    
    # 3. OCR 解析
    log("   🔍 解析财报数据...")
    result, error = parse_financial_data(pdf_files)
    if error:
        log(f"   ❌ {error}")
        void_customer(page, customer_name, VOID_REASONS['pdf_format_error'])
        return False
    
    bs_data, pl_data = result
    log(f"   BS: {sum(len(v) for v in bs_data.values())}项 / PL: {sum(len(v) for v in pl_data.values())}项")
    
    # 4. 评级门槛检查
    eligible, reason = check_eligibility(bs_data, pl_data)
    if not eligible:
        log(f"   ❌ 不满足门槛: {reason}")
        void_customer(page, customer_name, reason)
        return False
    
    log("   ✅ 通过评级门槛")
    
    # 5. 填写模板
    output_path = WORK_DIR / f"{customer_name}_download" / f"{customer_name}_报表模板.xlsx"
    fill_template(customer_name, bs_data, pl_data, TEMPLATE_PATH, output_path)
    log(f"   ✅ 模板已生成: {output_path.name}")
    
    # 6. 上传财报
    upload_financial(page, output_path)
    log(f"   ✅ 财报已上传")
    
    # 7. 评级
    click_rate_button(page)
    
    # 8. 返回 + 推送
    click_back(page)
    click_push(page, customer_name)
    
    log(f"   🎉 {customer_name} 全部完成!")
    return True


def main():
    parser = argparse.ArgumentParser(description='BSP 曼德评级自动化')
    parser.add_argument('--auto', action='store_true', help='自动处理全部待评级')
    parser.add_argument('--customer', type=str, help='指定客户名')
    args = parser.parse_args()
    
    # 启动 Chrome
    ensure_chrome()
    
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f'http://127.0.0.1:9222')
        ctx = browser.contexts[0]
        page = ctx.new_page()
        
        # 登录
        log("🔑 登录 BSP...")
        logged_in = login(page)
        if not logged_in:
            input("   按回车继续（请在 Chrome 中完成登录）...")
        
        # ── 交互式选择 ──
        if args.customer:
            # 指定客户
            process_single(page, args.customer)
            
        elif args.auto:
            # 全自动 - 遍历待评级
            customers = get_customer_list(page)
            for i, c in enumerate(customers):
                log(f"\n[{i+1}/{len(customers)}] {c['name']}")
                process_single(page, c['name'])
                if i < len(customers) - 1:
                    log("⏳ 等待3秒后继续...")
                    time.sleep(3)
        else:
            # 交互式菜单
            while True:
                customers = get_customer_list(page)
                
                print(f"\n{'='*50}")
                print(f"  待评级客户: {len(customers)} 户")
                print(f"{'='*50}")
                for i, c in enumerate(customers[:10]):
                    print(f"  {i+1}. {c['name']} ({c['code']})")
                if len(customers) > 10:
                    print(f"     ... 还有 {len(customers)-10} 户")
                print(f"  a. 全部自动处理")
                print(f"  q. 退出")
                print(f"{'='*50}")
                
                choice = input("选择 (1-10/a/q): ").strip()
                if choice == 'q':
                    break
                elif choice == 'a':
                    for i, c in enumerate(customers):
                        log(f"\n[{i+1}/{len(customers)}]")
                        process_single(page, c['name'])
                        time.sleep(2)
                    break
                elif choice.isdigit() and 1 <= int(choice) <= len(customers):
                    idx = int(choice) - 1
                    process_single(page, customers[idx]['name'])
                    input("\n按回车继续...")
                else:
                    print("无效选择")
        
        browser.close()
    
    log("\n🎉 全部操作完成!")


if __name__ == '__main__':
    main()
