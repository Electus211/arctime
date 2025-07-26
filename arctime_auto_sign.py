import requests
import logging
import json
import re
import sys
import io
import os
import smtplib
import time
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

def send_qq_email(subject, content):
    """发送QQ邮件通知（使用MATL_前缀变量）"""
    try:
        smtp_server = os.getenv('MATL_SMTP_SERVER', 'smtp.qq.com')
        smtp_port = int(os.getenv('SMTP_PORT', 465))
        sender = os.getenv('MATL_USERNAME')
        password = os.getenv('MATL_PASSWORD')
        receivers = [r.strip() for r in os.getenv('MATL_TO', '').split(',') if r.strip()]
        
        if not all([sender, password, receivers]):
            logger.warning("邮件配置不完整，跳过发送")
            return False
            
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = Header(f"Arctime签到通知 <{sender}>")
        msg['To'] = Header(",".join(receivers))
        msg['Subject'] = Header(subject)
        
        for attempt in range(3):
            try:
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(sender, password)
                    server.sendmail(sender, receivers, msg.as_string())
                logger.info("邮件发送成功")
                return True
            except Exception as e:
                logger.warning(f"邮件发送失败（尝试 {attempt+1}/3）: {str(e)}")
                time.sleep(2)
        return False
    except Exception as e:
        logger.error(f"邮件发送异常: {str(e)}")
        return False

def arctime_login():
    """使用USERNAME/PASSWORD环境变量登录"""
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    
    if not username or not password:
        logger.error("请设置USERNAME和PASSWORD环境变量")
        return None
    
    session = requests.Session()
    try:
        response = session.post(
            "https://m.arctime.cn/home/user/login_save.html",
            data={"username": username, "password": password, "login_type": "2"},
            headers={
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest"
            },
            verify=False
        )
        if response.json().get("status") == 1:
            logger.info("登录成功")
            return session
        logger.error("登录失败")
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
    return None

def arctime_sign(session):
    """签到主逻辑"""
    sign_urls = [
        ("POST", "https://m.arctime.cn/api/user/sign"),
        ("POST", "https://api.arctime.cn/v1/user/sign"),
        ("GET", "https://m.arctime.cn/home/user/do_sign")
    ]
    
    for method, url in sign_urls:
        try:
            response = session.request(method, url, verify=False, timeout=10)
            if "今日已签到" in response.text or response.json().get("status") == 1:
                logger.info(f"签到成功（{url}）")
                return True, f"{method} {url} 成功"
        except Exception as e:
            logger.warning(f"接口 {url} 异常: {str(e)}")
    
    logger.error("所有签到接口尝试失败")
    return False, "签到失败"

if __name__ == "__main__":
    logger.info("======== 任务开始 ========")
    
    # 执行签到
    session = arctime_login()
    status, message = (False, "登录失败") if not session else arctime_sign(session)
    
    # 发送通知
    if os.getenv('ENABLE_EMAIL') == 'true':
        email_content = f"""
        Arctime签到结果：
        时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
        状态: {"成功" if status else "失败"}
        详情: {message}
        """
        send_qq_email(f"Arctime签到{'成功' if status else '失败'}", email_content)
    
    logger.info("======== 任务结束 ========")
    sys.exit(0 if status else 1)
