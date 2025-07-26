import requests
import logging
import json
import sys
import io
import os
import time
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

# ================ Arctime登录 ================
def arctime_login():
    try:
        # 从环境变量获取账号密码
        username = os.getenv('ARCTIME_USERNAME')
        password = os.getenv('ARCTIME_PASSWORD')
        
        if not username or not password:
            logger.error("未设置环境变量ARCTIME_USERNAME或ARCTIME_PASSWORD")
            return None
            
        session = requests.Session()
        login_url = "https://m.arctime.cn/home/user/login_save.html"
        
        # 使用您本地成功的请求配置
        payload = {
            "username": username,
            "password": password,
            "login_type": "2"
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0"
        }
        
        response = session.post(login_url, data=payload, headers=headers, verify=False)
        response.encoding = 'utf-8'
        
        # 调试日志 - 只在需要时启用
        if os.getenv('DEBUG') == 'true':
            logger.debug(f"登录响应状态码: {response.status_code}")
            logger.debug(f"登录响应内容: {response.text[:200]}")
        
        data = response.json()
        if data.get("status") == 1:
            logger.info("登录成功")
            return session
        else:
            logger.error(f"登录失败: {data.get('msg', '未知错误')}")
            return None
            
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return None

# ================ Arctime签到 ================
def arctime_sign(session):
    if not session:
        logger.error("无法签到：未登录或会话无效")
        return False
        
    try:
        # 使用您本地成功的接口列表
        sign_urls = [
            ("https://m.arctime.cn/api/user/sign", 10),
            ("https://api.arctime.cn/v1/user/sign", 10)
        ]
        
        for url, timeout in sign_urls:
            try:
                logger.info(f"尝试签到接口: {url}")
                response = session.post(url, verify=False, timeout=timeout)
                response.encoding = 'utf-8'
                
                # 调试日志 - 只在需要时启用
                if os.getenv('DEBUG') == 'true':
                    logger.debug(f"接口响应状态码: {response.status_code}")
                    logger.debug(f"接口响应内容: {response.text[:200]}")
                
                # 检查响应内容
                if "今日已签到" in response.text:
                    logger.info(f"今日已签到（接口: {url}）")
                    return True
                    
                try:
                    data = response.json()
                    if data.get("status") == 1 or "操作成功" in data.get("msg", ""):
                        logger.info(f"签到成功（接口: {url}）")
                        return True
                except json.JSONDecodeError:
                    pass  # 非JSON格式继续检查文本
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"接口 {url} 请求异常: {str(e)}")

        # 检查用户中心页面
        try:
            logger.info("尝试通过用户中心页面确认签到状态...")
            response = session.get("https://m.arctime.cn/home/ucenter", verify=False, timeout=10)
            response.encoding = 'utf-8'
            
            if "今日已签到" in response.text or "操作成功" in response.text:
                logger.info("页面检测: 今日已签到")
                return True
                
            logger.error("无法确认签到状态")
        except requests.exceptions.RequestException as e:
            logger.error(f"用户中心请求失败: {str(e)}")
            
        return False

    except Exception as e:
        logger.error(f"签到流程异常: {str(e)}")
        return False

# ================ 主程序 ================
if __name__ == "__main__":
    logger.info("======== Arctime自动签到开始 ========")
    
    # 执行登录和签到
    session = arctime_login()
    sign_result = False
    if session:
        sign_result = arctime_sign(session)
    
    # 输出最终结果
    logger.info(f"签到结果: {'成功' if sign_result else '失败'}")
    logger.info("======== Arctime自动签到结束 ========")
    
    # 如果签到失败，退出码为1（触发工作流失败通知）
    if not sign_result:
        sys.exit(1)
