import requests
import logging
import json
import re
import sys
import io
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ================ 初始化设置 ================
# 修复控制台编码
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
    session = requests.Session()
    login_url = "https://m.arctime.cn/home/user/login_save.html"
    
    # 从环境变量获取账号密码
    username = os.getenv('ARCTIME_USERNAME', 'Electus')
    password = os.getenv('ARCTIME_PASSWORD', 'Electus321')
    
    payload = {
        "username": username,
        "password": password,
        "login_type": "2"
    }
    
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Origin": "https://m.arctime.cn",
        "Referer": "https://m.arctime.cn/home/user/login.html",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    try:
        logger.info("正在登录Arctime...")
        response = session.post(login_url, data=payload, headers=headers, verify=False)
        response.encoding = 'utf-8'
        
        # 调试日志
        logger.debug("登录响应状态码: %d", response.status_code)
        logger.debug("登录响应内容: %s", response.text[:300])
        
        try:
            data = response.json()
            if data.get("status") == 1:
                logger.info("登录成功")
                return session
            logger.error("登录失败: %s", data.get("msg", "未知错误"))
        except json.JSONDecodeError:
            logger.error("登录响应非JSON格式: %s", response.text[:100])
    except Exception as e:
        logger.error("登录异常: %s", str(e))
    return None

# ================ Arctime签到 ================
def arctime_sign(session):
    if session is None:
        logger.error("无法签到：未登录或会话无效")
        return False
        
    try:
        # 扩展可能的签到接口
        sign_urls = [
            ("POST", "https://m.arctime.cn/api/user/sign", 5),
            ("POST", "https://api.arctime.cn/v1/user/sign", 5),
            ("GET", "https://m.arctime.cn/home/user/do_sign", 5),
            ("POST", "https://m.arctime.cn/user/sign_in", 5)
        ]
        
        # 更新会话头信息
        session.headers.update({
            "Referer": "https://m.arctime.cn/home/ucenter",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        })
        
        for method, url, timeout in sign_urls:
            try:
                logger.info("尝试签到接口: %s %s", method, url)
                
                if method == "POST":
                    response = session.post(url, verify=False, timeout=timeout)
                else:
                    response = session.get(url, verify=False, timeout=timeout)
                
                response.encoding = 'utf-8'
                
                # 调试日志
                logger.debug("接口 %s 响应状态码: %d", url, response.status_code)
                logger.debug("接口 %s 响应内容: %s", url, response.text[:300])
                
                # 检查响应内容
                if "今日已签到" in response.text:
                    logger.info("今日已签到（接口: %s）", url)
                    return True
                    
                if "status" in response.text:
                    try:
                        data = response.json()
                        if data.get("status") == 1 or "成功" in data.get("msg", ""):
                            logger.info("签到成功（接口: %s）", url)
                            return True
                    except:
                        pass  # 非JSON格式继续检查文本
                
                if "操作成功" in response.text:
                    logger.info("签到成功（接口: %s）", url)
                    return True
                    
            except requests.exceptions.RequestException as e:
                logger.warning("接口 %s 请求异常: %s", url, str(e))

        # 检查用户中心页面确认签到状态
        logger.info("尝试通过用户中心页面确认签到状态...")
        try:
            response = session.get("https://m.arctime.cn/home/ucenter", verify=False, timeout=10)
            response.encoding = 'utf-8'
            
            # 调试日志
            logger.debug("用户中心响应状态码: %d", response.status_code)
            logger.debug("用户中心响应内容: %s", response.text[:300])
            
            # 检查签到状态
            if "今日已签到" in response.text:
                logger.info("页面检测: 今日已签到")
                return True
                
            if "操作成功" in response.text:
                logger.info("页面检测: 签到成功")
                return True
                
            # 尝试提取签到状态
            sign_status = re.search(r'class="sign-status">(.+?)<', response.text)
            if sign_status:
                status_text = sign_status.group(1)
                if "已签到" in status_text or "成功" in status_text:
                    logger.info("页面检测: %s", status_text)
                    return True
                    
            logger.error("无法确认签到状态，最后响应: %s", response.text[:200])
        except requests.exceptions.RequestException as e:
            logger.error("用户中心请求失败: %s", str(e))
            
        return False

    except Exception as e:
        logger.error("签到流程异常: %s", str(e))
        return False

# ================ 主程序 ================
if __name__ == "__main__":
    logger.info("======== Arctime自动签到开始 ========")
    
    # 检查环境变量
    if not os.getenv('ARCTIME_USERNAME') or not os.getenv('ARCTIME_PASSWORD'):
        logger.warning("未设置环境变量ARCTIME_USERNAME/ARCTIME_PASSWORD，使用默认账号")
    
    # 执行登录和签到
    session = arctime_login()
    if session:
        sign_result = arctime_sign(session)
        logger.info("签到结果: %s", "成功" if sign_result else "失败")
    else:
        logger.error("登录失败，无法执行签到")
    
    logger.info("======== Arctime自动签到结束 ========")
    logger.info("===== 任务结束 =====")
