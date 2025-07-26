import requests
import logging
import json
import sys
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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
            "Referer": "https://m.arctime.cn/home/user/login.html",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        response = session.post(login_url, data=payload, headers=headers, 
                              verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        logger.debug(f"原始响应: {response.text}")
        
        # 特殊处理Arctime的反逻辑响应
        if '"status":0' in response.text and '"msg":"登录成功"' in response.text:
            logger.info("检测到特殊响应格式：status=0但msg=登录成功")
            return session
            
        try:
            data = response.json()
            if data.get("status") == 1 or "登录成功" in data.get("msg", ""):
                return session
            logger.error(f"登录失败: {data.get('msg', '未知错误')}")
        except json.JSONDecodeError:
            if "登录成功" in response.text:
                return session
            logger.error(f"响应解析失败: {response.text[:200]}")
            
        return None
            
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return None

def arctime_sign(session):
    try:
        # 尝试所有已知接口
        endpoints = [
            ("POST", "https://m.arctime.cn/api/user/sign"),
            ("GET", "https://m.arctime.cn/home/user/do_sign"),
            ("POST", "https://api.arctime.cn/v1/user/sign")
        ]
        
        for method, url in endpoints:
            try:
                logger.debug(f"尝试 {method} {url}")
                response = session.request(method, url, verify=False, timeout=10)
                response.encoding = 'utf-8'
                
                if '{"status":1}' in response.text or "今日已签到" in response.text:
                    logger.info(f"{url} 签到成功")
                    return True
                    
                # 特殊处理矛盾响应
                if '"status":0' in response.text and "操作成功" in response.text:
                    logger.info("检测到特殊成功响应")
                    return True
                    
            except Exception as e:
                logger.warning(f"接口 {url} 异常: {str(e)}")
                
        logger.error("所有接口尝试失败")
        return False
        
    except Exception as e:
        logger.error(f"签到异常: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("======== 开始执行 ========")
    success = False
    
    if session := arctime_login():
        logger.info("登录成功")
        if arctime_sign(session):
            logger.info("签到成功")
            success = True
        else:
            logger.error("签到失败")
    else:
        logger.error("登录失败")
        
    logger.info("======== 执行结束 ========")
    sys.exit(0 if success else 1)
