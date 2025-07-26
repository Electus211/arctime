import requests
import logging
import json
import re
import sys
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================ 日志配置 ================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================ QQ邮件通知 ================
def send_qq_email(subject, content):
    """发送QQ邮件通知"""
    try:
        # 从环境变量获取邮件配置
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
        smtp_port = int(os.getenv('SMTP_PORT', 465))
        sender = os.getenv('EMAIL_SENDER')
        password = os.getenv('EMAIL_PASSWORD')  # QQ邮箱使用授权码
        receivers = os.getenv('EMAIL_RECEIVER').split(',')  # 多个收件人用逗号分隔
        
        if not sender or not password or not receivers:
            logger.warning("邮件配置不完整，跳过发送")
            return False
            
        # 创建邮件内容
        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = Header(sender, 'utf-8')
        message['To'] = Header(",".join(receivers), 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')
        
        # 发送邮件（带重试机制）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if smtp_port == 465:
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                else:
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.starttls()  # 启用TLS加密
                
                server.login(sender, password)
                server.sendmail(sender, receivers, message.as_string())
                server.quit()
                logger.info("邮件发送成功（尝试 %d/%d）", attempt+1, max_retries)
                return True
            except Exception as e:
                logger.warning("邮件发送失败（尝试 %d/%d）: %s", attempt+1, max_retries, str(e))
        
        return False
    except Exception as e:
        logger.error("邮件发送异常: %s", str(e))
        return False

# ================ Arctime登录 ================
def arctime_login():
    session = requests.Session()
    login_url = "https://m.arctime.cn/home/user/login_save.html"
    
    # 从环境变量获取账号密码
    username = os.getenv('ARCTIME_USERNAME')
    password = os.getenv('ARCTIME_PASSWORD')
    
    if not username or not password:
        logger.error("未设置ARCTIME_USERNAME或ARCTIME_PASSWORD环境变量")
        return None
    
    payload = {
        "username": username,
        "password": password,
        "login_type": "2"
    }
    
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Origin": "https://m.arctime.cn",
        "Referer": "https://m.arctime.cn/home/user/login.html",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    try:
        logger.info("正在登录Arctime...")
        response = session.post(login_url, data=payload, headers=headers, verify=False)
        response.encoding = 'utf-8'
        
        try:
            data = response.json()
            if data.get("status") == 1:
                logger.info("登录成功")
                return session
            logger.error("登录失败: %s", data.get("msg", "未知错误"))
        except json.JSONDecodeError:
            logger.error("登录响应非JSON格式: %s", response.text[:100])
    except Exception as e:
        logger.error("登录异常: %s", str(e))
    return None

# ================ Arctime签到 ================
def arctime_sign(session):
    if session is None:
        logger.error("无法签到：未登录或会话无效")
        return False
        
    try:
        # 扩展可能的签到接口
        sign_urls = [
            ("POST", "https://m.arctime.cn/api/user/sign", 5),
            ("POST", "https://api.arctime.cn/v1/user/sign", 5),
            ("GET", "https://m.arctime.cn/home/user/do_sign", 5),
            ("POST", "https://m.arctime.cn/user/sign_in", 5)
        ]
        
        # 更新会话头信息
        session.headers.update({
            "Referer": "https://m.arctime.cn/home/ucenter",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        })
        
        sign_success = False
        sign_message = ""
        
        for method, url, timeout in sign_urls:
            try:
                logger.info("尝试签到接口: %s %s", method, url)
                
                if method == "POST":
                    response = session.post(url, verify=False, timeout=timeout)
                else:
                    response = session.get(url, verify=False, timeout=timeout)
                
                response.encoding = 'utf-8'
                
                # 检查响应内容
                if "今日已签到" in response.text:
                    sign_message = f"今日已签到（接口: {url}）"
                    logger.info(sign_message)
                    sign_success = True
                    break
                    
                if "status" in response.text:
                    try:
                        data = response.json()
                        if data.get("status") == 1 or "成功" in data.get("msg", ""):
                            sign_message = f"签到成功（接口: {url}）"
                            logger.info(sign_message)
                            sign_success = True
                            break
                    except:
                        pass  # 非JSON格式继续检查文本
                
                if "操作成功" in response.text:
                    sign_message = f"签到成功（接口: {url}）"
                    logger.info(sign_message)
                    sign_success = True
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.warning("接口 %s 请求异常: %s", url, str(e))

        # 如果所有接口都失败，检查用户中心页面
        if not sign_success:
            logger.info("尝试通过用户中心页面确认签到状态...")
            try:
                response = session.get("https://m.arctime.cn/home/ucenter", verify=False, timeout=10)
                response.encoding = 'utf-8'
                
                # 检查签到状态
                if "今日已签到" in response.text:
                    sign_message = "页面检测: 今日已签到"
                    logger.info(sign_message)
                    sign_success = True
                    
                elif "操作成功" in response.text:
                    sign_message = "页面检测: 签到成功"
                    logger.info(sign_message)
                    sign_success = True
                    
                else:
                    # 尝试提取签到状态
                    sign_status = re.search(r'class="sign-status">(.+?)<', response.text)
                    if sign_status:
                        status_text = sign_status.group(1)
                        if "已签到" in status_text or "成功" in status_text:
                            sign_message = f"页面检测: {status_text}"
                            logger.info(sign_message)
                            sign_success = True
                    
            except requests.exceptions.RequestException as e:
                logger.error("用户中心请求失败: %s", str(e))
        
        return sign_success, sign_message

    except Exception as e:
        logger.error("签到流程异常: %s", str(e))
        return False, f"签到异常: {str(e)}"

# ================ 主程序 ================
if __name__ == "__main__":
    logger.info("======== Arctime自动签到开始 ========")
    sign_result = False
    sign_message = "未执行签到"
    
    # 执行登录和签到
    session = arctime_login()
    if session:
        sign_result, sign_message = arctime_sign(session)
    
    # 准备邮件内容
    status = "成功" if sign_result else "失败"
    subject = f"Arctime签到通知 - {status}"
    content = f"""
    Arctime自动签到结果：
    - 时间: {os.popen('date').read().strip()}
    - 状态: {status}
    - 详情: {sign_message}
    
    GitHub Actions运行日志：
    - 仓库: {os.getenv('GITHUB_REPOSITORY', '未知仓库')}
    - 运行ID: {os.getenv('GITHUB_RUN_ID', '未知')}
    - 日志链接: {os.getenv('GITHUB_SERVER_URL', '')}/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}
    """
    
    # 发送邮件通知
    if os.getenv('ENABLE_EMAIL') == 'true':
        logger.info("正在发送邮件通知...")
        email_sent = send_qq_email(subject, content)
        logger.info("邮件发送状态: %s", "成功" if email_sent else "失败")
    else:
        logger.info("未启用邮件通知")
    
    logger.info("======== Arctime自动签到结束 ========")
    
    # 如果签到失败，退出码为1（触发工作流失败通知）
    if not sign_result:
        sys.exit(1)
