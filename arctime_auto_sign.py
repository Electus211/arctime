import requests
import logging
import json
import sys
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================ 终极登录方案 ================
def arctime_login():
    try:
        session = requests.Session()
        login_url = "https://m.arctime.cn/home/user/login_save.html"
        
        payload = {
            "username": os.getenv('ARCTIME_USERNAME'),
            "password": os.getenv('ARCTIME_PASSWORD'),
            "login_type": "2"
        }
        
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://m.arctime.cn/home/user/login.html"
        }
        
        response = session.post(login_url, data=payload, headers=headers, 
                              verify=False, timeout=10)
        response.encoding = 'utf-8'
        
        # 终极响应解析方案
        if '{"status":1}' in response.text:  # 直接检测成功标志
            logger.info("登录成功")
            return session
        else:
            logger.error(f"登录失败 - 原始响应: {response.text[:100]}")
            return None
            
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return None

# ================ 可靠签到方案 ================
def arctime_sign(session):
    try:
        # 主接口
        response = session.post(
            "https://m.arctime.cn/api/user/sign",
            verify=False,
            timeout=10
        )
        
        # 终极结果检测
        if '{"status":1}' in response.text or "今日已签到" in response.text:
            logger.info("签到成功")
            return True
            
        # 备用检测方案
        response = session.get(
            "https://m.arctime.cn/home/ucenter",
            verify=False,
            timeout=10
        )
        if "今日已签到" in response.text:
            logger.info("通过用户中心检测到已签到")
            return True
            
        logger.error(f"无法确认签到状态 - 最后响应: {response.text[:200]}")
        return False
        
    except Exception as e:
        logger.error(f"签到异常: {str(e)}")
        return False

# ================ 主程序 ================
if __name__ == "__main__":
    logger.info("======== 开始执行 ========")
    
    if session := arctime_login():
        if arctime_sign(session):
            sys.exit(0)  # 成功退出码
        else:
            logger.error("签到流程失败")
    else:
        logger.error("登录流程失败")
        
    logger.info("======== 执行结束 ========")
    sys.exit(1)  # 失败退出码
