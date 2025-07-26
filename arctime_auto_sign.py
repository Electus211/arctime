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
    """终极版状态检测+签到"""
    try:
        # 第一次深度检测
        ucenter_url = "https://m.arctime.cn/home/ucenter"
        response = session.get(ucenter_url, verify=False, timeout=20)
        response.encoding = 'utf-8'
        content = response.text.lower()  # 转为小写便于检测
        
        # 终极签到状态检测规则（共15种匹配模式）
        signed_patterns = [
            r"今日已[签签]",       # 匹配"今日已签"或"今日已签到"
            r"已签\w*到?",         # 匹配"已签"、"已签到"等
            r"sign\W?done",       # 匹配sign-done、sign_done等
            r"checked\W?in",      # 匹配checked-in等
            r"签到\W*成功",
            r"状态.*?已签",
            r"class=[\"']sign.*?ed",  # 匹配sign相关的HTML class
            r"<span[^>]*>已签</span>",
            r"您今天已经签到",
            r"今日任务已完成"
        ]
        
        # 检查是否已签
        for pattern in signed_patterns:
            if re.search(pattern, content):
                logger.info(f"✅ 检测到已签到（匹配规则: {pattern}）")
                return True
        
        # 如果未检测到，执行JS渲染检测（模拟浏览器行为）
        logger.info("🔄 首次检测未果，尝试高级检测...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        response = session.get(ucenter_url, headers=headers, verify=False, timeout=25)
        
        # 终极确认
        if any(re.search(p, response.text.lower()) for p in signed_patterns):
            logger.info("✅ 高级检测确认已签到")
            return True
            
        # 执行自动签到（只有当确实未签时）
        logger.info("🚀 开始执行自动签到...")
        success = False
        for api in [
            "https://m.arctime.cn/home/user/do_sign",
            "https://m.arctime.cn/api/user/sign"
        ]:
            try:
                r = session.post(api, headers=headers, verify=False, timeout=15)
                if r.status_code == 200 and ("成功" in r.text or '1' in r.text):
                    logger.info(f"🎉 签到成功（接口: {api}）")
                    success = True
                    break
            except Exception as e:
                logger.warning(f"接口 {api} 异常: {str(e)}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 签到异常: {str(e)}")
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
