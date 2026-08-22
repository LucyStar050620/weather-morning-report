# 每日天气早报（推送到微信）

一个零成本的天气推送小程序：每天早上 **北京时间 6:00** 自动运行，把**当前天气 + 未来 24 小时 + 穿衣指数 + 餐饮指数**以表格形式推送到你的微信。

- 🌍 天气数据：[Open-Meteo](https://open-meteo.com)（**免 API Key**）
- 📲 推送渠道：[Server酱 / ServerChan](https://sct.ftqq.com)（免费，微信扫码接收）
- ⚙️ 运行平台：GitHub Actions（免费，定时任务）

## 包含的内容

| 板块 | 说明 |
| --- | --- |
| 当前天气 | 天气状况、气温、体感温度、湿度、风速、更新时间 |
| 未来24小时 | 每 3 小时一行：天气、气温、降水概率 |
| 生活指数 | 穿衣指数（按气温自动分级）、餐饮指数（按气温/降雨自动建议） |

> 穿衣/餐饮指数为脚本根据气温、湿度、降雨情况自动计算，非官方指数。

## 文件结构

```
weather-morning-report/
├── weather.py                      # 主程序
├── requirements.txt                # Python 依赖
├── deploy.sh                       # 一键部署脚本
├── README.md
└── .github/workflows/
    └── daily-weather.yml           # GitHub Actions 定时任务
```

## 一、本地预览（无需任何账号）

```bash
pip install -r requirements.txt
python weather.py          # 默认城市 郑州，仅打印表格，不推送
CITY="上海" python weather.py
```

## 二、获取 Server酱 SendKey

1. 打开 https://sct.ftqq.com ，用微信扫码登录。
2. 在「发送消息」页复制你的 **SendKey**（形如 `SCTxxxxx`）。

## 三、部署到 GitHub 自动运行

### 方式 A：一键脚本（推荐）

在 `weather-morning-report` 目录内执行：

```bash
bash deploy.sh
```

脚本会：安装 gh（如没有）→ 引导你登录 GitHub → 创建仓库并推送 → 让你填入 SendKey 存为 Secret。
完成后每天北京时间早 6 点自动推送。

### 方式 B：手动部署

```bash
# 1. 登录 GitHub CLI
gh auth login

# 2. 提交并推送
git init
git add .
git commit -m "init weather report"
gh repo create weather-morning-report --public --source=. --remote=origin --push

# 3. 配置 Secrets（Settings -> Secrets -> Actions）
gh secret set SERVERCHAN_SENDKEY -b "你的SendKey"
# 可选：修改默认城市
gh secret set CITY -b "郑州"
```

## 四、定时说明

- 工作流使用 UTC 时间：`0 22 * * *` = **北京时间次日 06:00**。
- 也可在仓库 **Actions → 每日天气早报 → Run workflow** 手动触发一次测试。
- GitHub 免费账户的定时任务偶尔会有几分钟延迟，属正常现象。

## 五、自定义

- **改城市**：设置仓库 Secret `CITY`（如 `北京`）；不设则默认 `郑州`。
- **改推送时间**：编辑 `.github/workflows/daily-weather.yml` 里的 cron（注意是 UTC）。
- **换推送渠道**：目前为 Server酱；如需 PushPlus / 企业微信，可替换 `push_serverchan()` 函数。
