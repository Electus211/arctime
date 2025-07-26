import requests
import logging
import sys
import os
import re
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://m.arctime.cn/home/user/login.html",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        response = session.post(login_url, data=payload, headers=headers, 
                              verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        # 特殊处理Arctime的反逻辑响应
        if '"status":0' in response.text and '"msg":"登录成功"' in response.text:
            logger.info("登录成功（兼容特殊响应格式）")
            return session
            
        if "登录成功" in response.text:
            logger.info("登录成功（文本检测）")
            return session
            
        logger.debug(f"登录响应内容: {response.text[:200]}")
        return None
            
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return None

def arctime_sign(session):
    try:
        # 尝试直接签到接口
        sign_url = "https://m.arctime.cn/api/user/sign"
        logger.info(f"尝试签到接口: {sign_url}")
        
        try:
            response = session.post(sign_url, verify=False, timeout=15)
            response.encoding = 'utf-8'
            
            # 调试输出响应内容
            logger.debug(f"签到响应内容: {response.text[:300]}")
            
            # 检测各种可能的成功响应
            if '{"status":1}' in response.text:
                logger.info("API返回签到成功")
                return True
                
            if "今日已签到" in response.text:
                logger.info("检测到'今日已签到'标记")
                return True
                
            if "操作成功" in response.text:
                logger.info("检测到'操作成功'标记")
                return True
                
            # 尝试解析JSON响应
            try:
                data = response.json()
                if data.get("status") == 1 or data.get("success") or "成功" in data.get("msg", ""):
                    logger.info("JSON解析签到成功")
                    return True
            except:
                pass
                
        except Exception as e:
            logger.warning(f"签到接口异常: {str(e)}")
        
        # 用户中心页面检测（主要方法）
        ucenter_url = "https://m.arctime.cn/home/ucenter"
        logger.info(f"尝试用户中心页面检测: {ucenter_url}")
        
        response = session.get(ucenter_url, verify=False, timeout=15)
        response.encoding = 'utf-8'
        
        # 调试输出响应内容
        logger.debug(f"用户中心页面内容: {response.text[:300]}")
        
        # 多种成功条件检测
        success_patterns = [
            r"今日已签到",  # 中文提示
            r"已签到",     # 简短提示
            r"sign-status",  # 可能是签到状态的HTML class
            r"签到成功",   # 成功提示
            r"sign\s*success",  # 可能的CSS类
            r"签到：已签",  # 可能的格式
            r"status.*已签"  # 状态包含已签
        ]
        
        for pattern in success_patterns:
            if re.search(pattern, response.text):
                logger.info(f"检测到签到成功模式: {pattern}")
                return True
                
        # 终极方法：检查签到按钮状态
        if '签到</button>' in response.text:
            logger.warning("检测到签到按钮，可能未签到")
        else:
            logger.info("未检测到签到按钮，可能已签到")
            return True
                
        logger.error("所有签到方式均失败")
        return False
        
    except Exception as e:
        logger.error(f"签到异常: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("======== Arctime自动签到开始 ========")
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
        
    logger.info("======== Arctime自动签到结束 ========")
    sys.exit(0 if success else 1)
