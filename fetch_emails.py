import os.path
import json # 新增：用于保存 JSON 文件
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def fetch_latest_emails():
    creds = Credentials.from_authorized_user_file('token.json')
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        print("未发现邮件。")
        return

    email_list = [] # 新增：用于临时存放邮件数据的列表

    print("正在拉取邮件并保存...")
    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        
        headers = txt['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "无主题")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "未知发件人")
        date = next((h['value'] for h in headers if h['name'] == 'Date'), "未知日期")
        
        # 新增：获取邮件的正文摘要（Snippet）
        snippet = txt.get('snippet', '无摘要')

        # 将这封邮件的数据整理成一个字典
        email_data = {
            "发件人": sender,
            "主题": subject,
            "日期": date,
            "摘要": snippet
        }
        email_list.append(email_data)

    # 新增：将列表数据写入本地的 emails.json 文件
    with open('emails.json', 'w', encoding='utf-8') as f:
        json.dump(email_list, f, ensure_ascii=False, indent=4)
        
    print("✅ 成功！邮件已保存到当前目录的 emails.json 文件中。")

if __name__ == '__main__':
    fetch_latest_emails()