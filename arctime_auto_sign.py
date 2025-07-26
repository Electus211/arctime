import requests
import logging
import sys
import os
import re
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================ 超强登录模块 ================
def arctime_login():
    """带自动重试的登录模块"""
    max_retries = 3
    for attempt in range(max_retries):
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
                                  verify=False, timeout=20)
            response.encoding = 'utf-8'
            
            # 增强响应检测
            if ('"status":1' in response.text or 
                ('"status":0' and "登录成功" in response.text) or
                "login_success" in response.text):
                logger.info(f"✅ 登录成功 (尝试 {attempt+1}/{max_retries})")
                return session
                
            logger.warning(f"⚠️ 登录响应异常: {response.text[:200]}")
            
        except Exception as e:
            logger.warning(f"⚠️ 登录异常 (尝试 {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
    
    logger.error("❌ 登录失败")
    return None

# ================ 终极签到模块 ================
def arctime_sign(session):
    """带多重验证的签到模块"""
    try:
        # 第一次状态检测
        ucenter_url = "https://m.arctime.cn/home/ucenter"
        response = session.get(ucenter_url, verify=False, timeout=25)
        response.encoding = 'utf-8'
        content = response.text.lower()
        
        # 18种签到状态检测规则
        signed_rules = [
            r"今日已签", r"已签\w*到?", r"sign.?done", 
            r"checked.?in", r"签到.?成功", r"状态.*?已签",
            r"class=[\"']sign", r"<span[^>]*>已签</span>",
            r"今日任务已完成", r"already.?checked", 
            r"sign.?status", r"签到状态.*?已",
            r"您今天已经签到", r"今日已打", 
            r"completed", r"finished", 
            r"任务完成", r"每日签到.*?已"
        ]
        
        # 规则检测
        for rule in signed_rules:
            if re.search(rule, content):
                logger.info(f"✅ 已签到 (匹配规则: {rule})")
                return True
                
        # 如果未检测到，执行深度检查
        logger.info("🔄 执行深度检测...")
        time.sleep(3)  # 等待页面可能的内容加载
        
        api_endpoints = [
            ("POST", "https://m.arctime.cn/home/user/do_sign"),
            ("GET", "https://m.arctime.cn/api/user/sign_status"),
            ("POST", "https://m.arctime.cn/v2/user/sign")
        ]
        
        # 尝试各接口获取状态
        for method, url in api_endpoints:
            try:
                r = session.request(method, url, timeout=15, verify=False)
                if r.status_code == 200 and ("已签" in r.text or '1' in r.text):
                    logger.info(f"✅ 接口确认已签到 ({url})")
                    return True
            except:
                continue
                
        # 最终签到执行
        logger.info("🚀 执行自动签到...")
        sign_apis = [
            ("POST", "https://m.arctime.cn/home/user/do_sign"),
            ("POST", "https://m.arctime.cn/api/user/sign"),
            ("GET", "https://m.arctime.cn/user/autosign")
        ]
        
        for method, url in sign_apis:
            try:
                r = session.request(method, url, timeout=20, verify=False)
                if r.status_code == 200 and ("成功" in r.text or '1' in r.text):
                    logger.info(f"🎉 签到成功 ({url})")
                    return True
            except Exception as e:
                logger.warning(f"⚠️ 接口异常 ({url}): {str(e)}")
                time.sleep(2)
        
        logger.error("❌ 所有签到尝试失败")
        return False
        
    except Exception as e:
        logger.error(f"❌ 签到异常: {str(e)}")
        return False

# ================ 主流程 ================
if __name__ == "__main__":
    logger.info("======== 🚀 Arctime终极签到系统启动 ========")
    
    # 带异常捕获的主流程
    try:
        if not (session := arctime_login()):
            sys.exit(1)
            
        if arctime_sign(session):
            logger.info("======== ✅ 签到流程完成 ========")
            sys.exit(0)
        else:
            logger.error("======== ❌ 签到失败 ========")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❗ 系统异常: {str(e)}")
        sys.exit(1)
