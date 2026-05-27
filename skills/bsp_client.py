"""
BSP 系统操作 Skill
登录 → 列表遍历 → 打包下载 → 上传财报 → 评级 → 推送 → 作废
"""
import os, re, shutil, subprocess, time
from pathlib import Path
from playwright.sync_api import Page
from config import ACCOUNT, PASSWORD, WORK_DIR, LIST_URL


def login(page: Page) -> bool:
    """登录 BSP（验证码需人工）"""
    page.goto('https://bsp.gwscf.com/login', wait_until='domcontentloaded')
    time.sleep(2)
    
    # 检查是否已登录
    if 'index' in page.url or 'mdfirm' in page.url:
        return True
    
    inputs = page.query_selector_all('input.el-input__inner')
    if len(inputs) >= 2:
        inputs[0].fill(ACCOUNT)
        inputs[1].fill(PASSWORD)
        print("   ⚠️ 请在 Chrome 中输入验证码并登录")
        return False
    return False


def get_customer_list(page: Page) -> list:
    """获取待评级客户列表"""
    page.goto(LIST_URL, wait_until='domcontentloaded')
    time.sleep(2)
    
    customers = page.evaluate('''() => {
        let rows = document.querySelectorAll("table tr");
        let result = [];
        for (let tr of rows) {
            let cells = tr.querySelectorAll("td");
            if (cells.length < 5) continue;
            result.push({
                name: cells[1]?.innerText?.trim() || "",
                code: cells[2]?.innerText?.trim() || "",
                appNo: cells[4]?.innerText?.trim() || "",
            });
        }
        return result;
    }''')
    print(f"   待评级: {len(customers)} 户")
    return customers


def click_rate(page: Page, customer_name: str) -> bool:
    """点击某客户的评级按钮"""
    page.goto(LIST_URL, wait_until='domcontentloaded')
    time.sleep(2)
    
    # 在待评级tab中找客户
    for btn in page.query_selector_all('button'):
        if btn.inner_text().strip() == '评级' and btn.is_visible():
            parent = btn.evaluate('''e => {
                let tr = e.closest("tr");
                return tr ? tr.querySelector("td:nth-child(2)")?.innerText?.trim() || "" : "";
            }''')
            if customer_name and customer_name not in parent:
                continue
            btn.click()
            time.sleep(3)
            print(f"   进入评分页: {page.url[:80]}...")
            return True
    
    print(f"   ❌ 未找到客户: {customer_name}")
    return False


def download_pdfs(page: Page, customer_name: str, customer_code: str) -> Path:
    """
    点击打包下载，解压到工作目录
    返回: 解压后的PDF文件夹路径
    """
    save_dir = WORK_DIR / f"{customer_name}_download"
    save_dir.mkdir(parents=True, exist_ok=True)
    
    with page.expect_download() as dl_info:
        for btn in page.query_selector_all('button'):
            if btn.inner_text().strip() == '打包下载' and btn.is_visible():
                btn.click()
                break
    
    dl = dl_info.value
    zip_path = save_dir / dl.suggested_filename
    dl.save_as(str(zip_path))
    print(f"   下载: {zip_path.name}")
    
    extract_dir = save_dir / "extracted"
    extract_dir.mkdir(exist_ok=True)
    subprocess.run(['unzip', '-o', str(zip_path), '-d', str(extract_dir)], capture_output=True)
    
    return extract_dir


def upload_financial(page: Page, excel_path: Path):
    """上传财报Excel"""
    btn = page.query_selector('button:has-text("上传财报")')
    if btn and btn.is_visible():
        btn.click()
        time.sleep(1.5)
    
    # 文件选择
    with page.expect_file_chooser() as fc_info:
        dragger = page.query_selector('.el-upload-dragger, .el-upload')
        if dragger:
            dragger.click()
        else:
            page.evaluate('document.querySelector("input[type=file]").click()')
    fc_info.value.set_files(str(excel_path))
    time.sleep(2)
    print("   文件已选择")
    
    # 点确定
    for btn in page.query_selector_all('button'):
        if btn.inner_text().strip() == '确 定' and btn.is_visible():
            btn.click()
            time.sleep(1.5)
            break
    
    # 处理系统确认弹窗
    for _ in range(3):
        for btn in page.query_selector_all('.el-message-box button'):
            if btn.inner_text().strip() == '确定' and btn.is_visible():
                btn.click()
                time.sleep(1)
        else:
            break


def click_rate_button(page: Page):
    """点击评分页的评级按钮"""
    for btn in page.query_selector_all('button'):
        if btn.inner_text().strip() == '评级' and btn.is_visible():
            btn.click()
            time.sleep(3)
            print(f"   评级完成: {page.url[:80]}")
            return True
    return False


def click_back(page: Page):
    """点击返回按钮"""
    for btn in page.query_selector_all('button'):
        if '返回' in btn.inner_text().strip() and btn.is_visible():
            btn.click()
            time.sleep(2)
            return


def click_push(page: Page, customer_name: str):
    """在已评级列表推送某客户"""
    if 'mdfirm' not in page.url:
        page.goto(LIST_URL, wait_until='domcontentloaded')
        time.sleep(2)
    
    # 切到已评级tab
    for el in page.query_selector_all('span, div'):
        t = el.inner_text().strip()
        if t.startswith('已评级'):
            el.click()
            time.sleep(2)
            break
    
    # 找推送按钮
    for btn in page.query_selector_all('button'):
        if btn.inner_text().strip() == '推送' and btn.is_visible():
            parent = btn.evaluate('''e => {
                let tr = e.closest("tr");
                return tr ? tr.querySelector("td:nth-child(2)")?.innerText?.trim() || "" : "";
            }''')
            if customer_name not in parent:
                continue
            btn.click()
            time.sleep(1.5)
            break
    
    # 确认推送
    for btn in page.query_selector_all('.el-message-box button'):
        if btn.inner_text().strip() == '确定' and btn.is_visible():
            btn.click()
            time.sleep(2)
            print(f"   ✅ {customer_name} 推送成功")
            return True
    return False


def void_customer(page: Page, customer_name: str, reason: str):
    """
    在待评级列表作废某客户
    """
    if 'mdfirm' not in page.url:
        page.goto(LIST_URL, wait_until='domcontentloaded')
        time.sleep(2)
    
    for btn in page.query_selector_all('button'):
        if btn.inner_text().strip() == '作废' and btn.is_visible():
            parent = btn.evaluate('''e => {
                let tr = e.closest("tr");
                return tr ? tr.querySelector("td:nth-child(2)")?.innerText?.trim() || "" : "";
            }''')
            if customer_name not in parent:
                continue
            btn.click()
            time.sleep(1.5)
            break
    
    # 填写原因
    page.fill('textarea', reason[:100])
    time.sleep(0.5)
    
    # 确认
    for btn in page.query_selector_all('.el-dialog button'):
        if btn.inner_text().strip() == '确认作废' and btn.is_visible():
            btn.click()
            time.sleep(2)
            print(f"   ✅ {customer_name} 作废已提交")
            return True
    return False
