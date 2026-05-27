# BSP 曼德评级自动化系统

长城供应链金融数据管理平台 — 曼德供应商评级全流程自动化。

## 功能

| 模式 | 说明 |
|------|------|
| `python3 main.py` | 交互式菜单，选择客户处理 |
| `python3 main.py --customer "企业名"` | 指定单户处理 |
| `python3 main.py --auto` | 全自动遍历全部待评级客户 |

## 处理流程

```
① 登录 BSP
② 进入待评级列表
③ 点击客户「评级」按钮 → 进评分页
④ 打包下载 3 年财报 PDF
⑤ OCR 解析财务数据 (MinerU预检 + TextIn精准)
⑥ 评级门槛判断
   ├── 通过 → ⑦ 填模板 → ⑧ 上传财报 → ⑨ 评级 → ⑩ 推送
   └── 不通过 → ⑪ 作废 + 填写原因
```

## 项目结构

```
bsp_automation/
├── main.py                  # 入口 - 交互式控制台
├── config.py                # 配置 (URL/账号/路径)
├── browser.py               # Chrome 调试管理器
├── requirements.txt         # Python 依赖
├── models/
│   ├── __init__.py
│   ├── bs_alias.py          # 资产负债表行名映射
│   └── pl_alias.py          # 利润表行名映射
├── skills/
│   ├── __init__.py
│   ├── pdf_parser.py        # OCR 双引擎解析 PDF
│   ├── template_filler.py   # 财报模板填写
│   ├── criteria.py          # 评级门槛 & 作废原因
│   └── bsp_client.py        # BSP 页面操作 (上传/评级/推送/作废)
├── data/
│   └── 模板.xlsx             # 标准财报模板
└── records/                 # 操作日志输出
```

## 数据输出

```
Desktop/工作/曼德/{客户名}_download/
├── {客户名}.zip               # 从 BSP 打包下载
├── extracted/                  # 解压后的 3 个 PDF
└── {客户名}_报表模板.xlsx       # 已填好数据的模板
```

## 首次使用

```bash
cd ~/.openclaw/workspace/bsp_automation
cp ../模板.xlsx data/
pip install -r requirements.txt
python3 main.py
```
