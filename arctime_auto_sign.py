import requests
import logging
import json
import sys
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别获取更多信息
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def arctime_login():
    try:
        # 调试输出环境变量
        logger.debug(f"尝试使用账号: {os.getenv('ARCTIME_USERNAME')}")
        
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
        
        # 打印完整请求信息
        logger.debug(f"请求URL: {login_url}")
        logger.debug(f"请求头: {headers}")
        logger.debug(f"请求数据: { {k:v[:1]+'***' if k=='password' else v for k,v in payload.items()} }")
        
        response = session.post(login_url, data=payload, headers=headers, 
                              verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        # 打印完整响应
        logger.debug(f"响应状态码: {response.status_code}")
        logger.debug(f"响应内容: {response.text}")
        
        try:
            data = response.json()
            if data.get("status") == 1:
                logger.info("登录成功")
                return session
            else:
                logger.error(f"登录失败 - 错误信息: {data.get('msg', '未知错误')}")
                return None
        except json.JSONDecodeError:
            logger.error(f"响应不是有效JSON: {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"登录过程异常: {str(e)}")
        return None

def arctime_sign(session):
    try:
        # 主签到接口
        sign_url = "https://m.arctime.cn/api/user/sign"
        logger.debug(f"尝试签到接口: {sign_url}")
        
        response = session.post(sign_url, verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        logger.debug(f"签到响应: {response.text[:200]}")
        
        if '{"status":1}' in response.text or "今日已签到" in response.text:
            logger.info("签到成功")
            return True
            
        # 备用检测
        ucenter_url = "https://m.arctime.cn/home/ucenter"
        logger.debug(f"尝试备用检测: {ucenter_url}")
        
        response = session.get(ucenter_url, verify=False, timeout=15)
        if "今日已签到" in response.text:
            logger.info("通过用户中心检测到已签到")
            return True
            
        logger.error("所有签到方式均失败")
        return False
        
    except Exception as e:
        logger.error(f"签到过程异常: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("======== 开始执行 ========")
    
    if session := arctime_login():
        if arctime_sign(session):
            sys.exit(0)
        else:
            logger.error("签到失败")
    else:
        logger.error("登录失败")
        
    logger.info("======== 执行结束 ========")
    sys.exit(1)
