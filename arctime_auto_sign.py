import requests
import logging
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def send_email(subject, content):
    """修复版邮件发送函数"""
    try:
        # 配置邮件内容
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = os.getenv('MATL_USERNAME')
        msg['To'] = os.getenv('MATL_TO')
        
        # 分步调试SMTP连接
        logger.info("正在连接SMTP服务器...")
        server = smtplib.SMTP(os.getenv('MATL_SMTP_SERVER'), 587, timeout=10)
        
        logger.info("启动TLS加密...")
        server.starttls()
        
        logger.info("尝试登录...")
        server.login(os.getenv('MATL_USERNAME'), os.getenv('MATL_PASSWORD'))
        
        logger.info("发送邮件...")
        server.send_message(msg)
        server.quit()
        logger.info("✅ 邮件发送成功")
    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {str(e)}")
        # 打印调试信息
        logger.debug(f"SMTP Server: {os.getenv('MATL_SMTP_SERVER')}")
        logger.debug(f"Username: {os.getenv('MATL_USERNAME')}")

def arctime_sign():
    """Arctime签到主逻辑"""
    session = requests.Session()
    result = {"login": False, "sign": False, "msg": []}
    
    # 登录
    try:
        login_url = "https://m.arctime.cn/home/user/login_save.html"
        payload = {
            "username": os.getenv('USERNAME'),
            "password": os.getenv('PASSWORD'),
            "login_type": "2"
        }
        res = session.post(login_url, data=payload, verify=False, timeout=10)
        data = res.json()
        
        if data.get("status") == 1:
            result["login"] = True
            result["msg"].append("✅ 登录成功")
            
            # 检查签到状态
            ucenter_res = session.get("https://m.arctime.cn/home/ucenter", verify=False)
            if "今日已签到" in ucenter_res.text:
                result["msg"].append("⏭️ 今日已签到")
            else:
                sign_res = session.post("https://m.arctime.cn/api/user/sign", verify=False)
                if sign_res.json().get("status") == 1:
                    result["sign"] = True
                    result["msg"].append("🎉 签到成功")
        else:
            result["msg"].append(f"❌ 登录失败: {data.get('msg')}")
            
    except Exception as e:
        result["msg"].append(f"🚨 系统异常: {str(e)}")
    
    return result

if __name__ == "__main__":
    logger.info("===== 任务开始 =====")
    result = arctime_sign()
    
    # 发送邮件通知
    email_content = "\n".join(result["msg"])
    email_subject = "Arctime签到通知 - " + ("成功" if result["sign"] else "失败")
    send_email(email_subject, email_content)
    
    logger.info("===== 任务结束 =====")
