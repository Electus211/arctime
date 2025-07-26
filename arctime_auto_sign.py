import requests
import logging
import sys
import os
import re
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================ 智能登录模块 ================
def arctime_login():
    """处理Arctime特殊登录逻辑"""
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
            "Referer": "https://m.arctime.cn/home/user/login.html",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        response = session.post(login_url, data=payload, headers=headers, 
                              verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        # 处理Arctime特殊响应格式
        if ('"status":0' in response.text and '"msg":"登录成功"' in response.text) or "登录成功" in response.text:
            logger.info("登录成功")
            return session
            
        logger.error(f"登录失败，响应内容: {response.text[:200]}")
        return None
            
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return None

# ================ 智能签到模块 ================
def arctime_sign(session):
    """包含状态检测和自动签到的完整逻辑"""
    try:
        # 1. 首先检查签到状态
        ucenter_url = "https://m.arctime.cn/home/ucenter"
        response = session.get(ucenter_url, verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        # 已签到检测（多种匹配模式）
        signed_patterns = [
            r"今日已签到", 
            r"已签(到|到成功)",
            r"sign-status.*?已签",
            r"签到.*?成功"
        ]
        
        for pattern in signed_patterns:
            if re.search(pattern, response.text, re.IGNORECASE):
                logger.info(f"检测到已签到标记: {pattern}")
                return True
        
        # 2. 如果未签到，执行自动签到
        logger.info("未检测到签到记录，开始自动签到...")
        
        # 尝试所有已知签到接口
        sign_apis = [
            ("POST", "https://m.arctime.cn/home/user/do_sign"),  # 主接口
            ("POST", "https://m.arctime.cn/api/user/sign"),      # 备用接口1
            ("GET", "https://m.arctime.cn/user/sign")            # 备用接口2
        ]
        
        for method, api in sign_apis:
            try:
                logger.info(f"尝试 {method} {api}")
                response = session.request(method, api, verify=False, timeout=10)
                
                # 成功检测（支持多种响应格式）
                if ('"status":1' in response.text or 
                    "操作成功" in response.text or 
                    "签到成功" in response.text):
                    logger.info(f"通过 {api} 签到成功")
                    return True
                    
            except Exception as e:
                logger.warning(f"接口 {api} 异常: {str(e)}")
        
        # 3. 最终确认
        logger.info("最终确认签到状态...")
        response = session.get(ucenter_url, verify=False, timeout=10)
        if "今日已签到" in response.text:
            logger.info("最终确认签到成功")
            return True
            
        logger.error("所有签到方式均失败")
        return False
        
    except Exception as e:
        logger.error(f"签到异常: {str(e)}")
        return False

# ================ 主执行流程 ================
if __name__ == "__main__":
    logger.info("======== Arctime自动签到系统启动 ========")
    
    # 执行登录
    if not (session := arctime_login()):
        logger.error("登录阶段失败，终止执行")
        sys.exit(1)
        
    # 执行签到
    if arctime_sign(session):
        logger.info("✅ 签到流程完成")
        sys.exit(0)
    else:
        logger.error("❌ 签到流程失败")
        sys.exit(1)
