# 📬 Email Manager Desktop (MVP)

用 Python + Streamlit 做的一个小型 Gmail 收件箱查看器：拉取最近几封邮件，缓存到本地 `emails.json`，然后在网页里展示（支持一键刷新）。

## 功能
- 展示最近邮件列表（发件人 / 主题 / 日期）
- 展示每封邮件的摘要
- 点击「🔄 刷新收件箱」后重新拉取并自动刷新页面
- 本地缓存 `emails.json`，避免每次打开都请求 API

## 技术栈
- Python 3.9+
- Streamlit
- Gmail API v1（Google API Python Client）
- OAuth 2.0（本地 `token.json`）

## 快速开始
### 1) 准备 Google 凭证
在 Google Cloud Console 创建 OAuth Client（Desktop app），下载 `credentials.json` 放到项目根目录。

首次授权后会在本地生成：
- `token.json`：访问令牌（请勿提交到仓库）
- `emails.json`：邮件缓存（可提交也可不提交，按你的习惯）

### 2) 安装依赖

```bash
pip install -r requirements.txt
```

### 3) 运行

```bash
streamlit run app.py
```

打开网页后，点击侧边栏的「🔄 刷新收件箱」即可拉取最新邮件并刷新展示。

## 常见问题
### 找不到 `emails.json`
这是正常的：第一次运行还没拉取过数据。直接在页面里点「🔄 刷新收件箱」即可生成。

### 授权/拉取失败
通常是以下原因：
- `credentials.json` 没放在项目根目录
- Google Cloud 项目的 OAuth 同意屏幕/测试用户没配置好
- `token.json` 过期或权限变更（可以删除 `token.json` 重新授权）