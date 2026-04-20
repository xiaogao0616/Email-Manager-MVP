import streamlit as st
import json
import pandas as pd
from fetch_emails import fetch_latest_emails

st.set_page_config(page_title="极简邮箱管家", layout="wide")


def load_emails() -> list:
    try:
        with open("emails.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


# --- 侧边栏 ---
with st.sidebar:
    st.header("📬 极简邮箱管家")
    st.markdown("基于 Gmail API 构建的轻量级邮件管理器。")
    st.divider()

    if st.button("🔄 刷新收件箱", use_container_width=True, type="primary"):
        with st.spinner("正在拉取最新邮件，请稍候…"):
            try:
                fetch_latest_emails()
                st.session_state["refresh_success"] = True
            except Exception as e:
                st.error(f"拉取失败：{e}")
                st.session_state["refresh_success"] = False
        st.rerun()

    if st.session_state.get("refresh_success"):
        st.success("✅ 收件箱已更新！")
        st.session_state["refresh_success"] = False


# --- 主区域 ---
st.title("📬 我的极简邮箱管家 MVP")

emails = load_emails()

if not emails:
    st.warning("暂无邮件数据，请点击左侧『🔄 刷新收件箱』按钮拉取。")
else:
    df = pd.DataFrame(emails)

    st.subheader("📥 最新收件箱")
    st.dataframe(
        df[["发件人", "主题", "日期"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("📖 邮件详情速览")
    for email in emails:
        with st.expander(f"来自: {email['发件人']} | {email['主题']}"):
            st.write(f"**时间:** {email['日期']}")
            st.info(f"**摘要:** {email['摘要']}")