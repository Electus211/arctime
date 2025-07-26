import requests
import os
from bs4 import BeautifulSoup

# 新版Arctime接口
LOGIN_URL = "https://www.arctime.com/login"
SIGN_URL = "https://www.arctime.com/api/user/sign"  # 示例接口，需实际抓包确认

def login(username, password):
    session = requests.Session()
    # 1. 获取登录页（提取csrf_token等）
    res = session.get(LOGIN_URL)
    soup = BeautifulSoup(res.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

    # 2. 提交登录表单
    data = {
        'username': username,
        'password': password,
        'csrf_token': csrf_token
    }
    res = session.post(LOGIN_URL, data=data)
    if "登录成功" in res.text:
        return session  # 返回已登录的session
    else:
        raise Exception("登录失败：请检查账号密码或网站改版")

def auto_sign(session):
    res = session.post(SIGN_URL)
    if res.json().get("success"):
        print("签到成功！")
    else:
        print("签到失败：", res.json().get("message"))

if __name__ == '__main__':
    username = os.getenv("USERNAME")  # 从GitHub Secrets读取
    password = os.getenv("PASSWORD")
    
    if not username or not password:
        raise ValueError("未设置USERNAME或PASSWORD环境变量")
    
    session = login(username, password)
    auto_sign(session)
