import time  # 用于延迟检测
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
    """增强版状态检测+签到"""
    try:
        # 第一次检测（带延迟）
        ucenter_url = "https://m.arctime.cn/home/ucenter"
        response = session.get(ucenter_url, verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        # 增强版已签到检测
        signed_keywords = [
            "今日已签到", "已签", "sign-done", 
            "已完成", "已打", "checked-in"
        ]
        
        # 检查是否已签
        if any(keyword in response.text for keyword in signed_keywords):
            logger.info("✅ 当前已签到（首次检测）")
            return True
            
        # 第二次检测（防止动态加载）
        logger.info("⚠️ 首次检测未发现签到记录，等待3秒后重试...")
        time.sleep(3)
        response = session.get(ucenter_url, verify=False, timeout=15)
        
        if any(keyword in response.text for keyword in signed_keywords):
            logger.info("✅ 当前已签到（二次检测）")
            return True
            
        # 执行自动签到（只有当确实未签时）
        logger.info("🔄 开始自动签到流程...")
        sign_apis = [
            ("POST", "https://m.arctime.cn/home/user/do_sign"),
            ("POST", "https://m.arctime.cn/api/user/sign")
        ]
        
        for method, api in sign_apis:
            try:
                response = session.request(method, api, verify=False, timeout=10)
                if '"status":1' in response.text or "成功" in response.text:
                    logger.info(f"🎉 签到成功（{api}）")
                    return True
            except Exception as e:
                logger.warning(f"接口 {api} 异常: {str(e)}")
                
        logger.error("❌ 所有签到尝试失败")
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
