"""BSP 自动化评级项目 - 配置"""
from pathlib import Path

# ── BSP 系统 ──
BSP_URL    = "https://bsp.gwscf.com"
INDEX_URL  = f"{BSP_URL}/index"
LOGIN_URL  = f"{BSP_URL}/login"
LIST_URL   = f"{BSP_URL}/riskcontrol/mdfirm"
CDP_PORT   = 9222

# ── 桌面路径 ──
DESKTOP         = Path.home() / "Desktop"
WORK_DIR        = DESKTOP / "工作" / "曼德"
TEMPLATE_PATH   = Path(__file__).parent / "data" / "模板.xlsx"
CRED_FILE       = Path(__file__).parent / ".bsp_cred"  # 缓存登录态

# ── Chrome ──
CHROME_APP     = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PROFILE  = Path.home() / "chrome-debug-profile"
CHROME_LOCK    = DEBUG_PROFILE / "SingletonLock"
CHROME_SOCK    = DEBUG_PROFILE / "SingletonSocket"
DEFAULT_PROFILE = Path.home() / "Library/Application Support/Google/Chrome"

# ── TextIn ──
TEXTIN_CONFIG  = Path.home() / ".openclaw" / "textin-config.json"
TEXTIN_API     = "https://api.textin.com/ai/service/v1/pdf_to_markdown"

# ── MinerU ──
MINERU_CONFIG  = Path.home() / ".openclaw" / "mineru-config.json"
MINERU_API     = "https://mineru.net/api/v1/agent/parse/file"

# ── BSP 账号 ──
ACCOUNT  = "GW00286650"
PASSWORD = "123456"
