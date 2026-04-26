import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# 核心：定义你的应用需要什么权限。
# 将 readonly 改为 modify，允许读取和修改邮件标签状态
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def main():
    creds = None
    
    # 检查是否已经有本地的 token.json 缓存
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # 如果没有有效的凭证，就引导用户（也就是你）去浏览器登录授权
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 这里会读取你刚刚下载的 credentials.json
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # 登录成功后，把令牌保存成 token.json，下次就不用再弹网页了！
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    print("🎉 恭喜！授权成功，已经成功获取并保存了 token.json！")

if __name__ == '__main__':
    main()