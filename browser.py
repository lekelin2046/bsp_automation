"""Chrome 调试浏览器管理"""
import os, shutil, subprocess, time, urllib.request
from pathlib import Path
from config import CHROME_APP, DEBUG_PROFILE, CHROME_LOCK, CHROME_SOCK, DEFAULT_PROFILE, CDP_PORT

log = lambda msg: print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def ensure_chrome() -> str:
    """确保调试 Chrome 在运行，返回 CDP URL"""
    for _ in range(2):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=2)
            log(f"✅ 调试 Chrome 已运行 (端口 {CDP_PORT})")
            return f"http://127.0.0.1:{CDP_PORT}"
        except:
            pass
    
    # 启动 Chrome
    log("🚀 启动调试 Chrome...")
    for lock in [CHROME_LOCK, CHROME_SOCK]:
        if lock.exists(): lock.unlink()
    
    if not (DEBUG_PROFILE / "Default").exists() and DEFAULT_PROFILE.exists():
        log("   复制 Chrome 配置...")
        shutil.copytree(str(DEFAULT_PROFILE), str(DEBUG_PROFILE),
                        symlinks=True, ignore_dangling_symlinks=True)
    
    subprocess.Popen(
        [CHROME_APP, f"--remote-debugging-port={CDP_PORT}",
         f"--user-data-dir={DEBUG_PROFILE}", "--window-position=-32000,0",
         "--remote-allow-origins=*"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid
    )
    for _ in range(15):
        time.sleep(1.5)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=2)
            log("✅ 调试 Chrome 已就绪")
            return f"http://127.0.0.1:{CDP_PORT}"
        except:
            continue
    
    raise RuntimeError("❌ Chrome 启动超时")
