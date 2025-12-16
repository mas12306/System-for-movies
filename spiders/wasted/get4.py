import requests
import threading
import parsel
import random
import time

# UA池
user_agents = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 OPR/26.0.1656.60',
    'Opera/8.0 (Windows NT 5.1; U; en)',
    'Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 9.50',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
    'Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2 ',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; SE 2.X MetaSr 1.0) ',
]

# 控制线程
lock = threading.Lock()


def verifyProxyList():
    '''
    验证ip有效性并存入valid.txt
    :return:
    '''
    # 确保文件存在
    try:
        proxyList = open('proxy.txt', 'r')
        valid = open('valid.txt', 'a')
    except FileNotFoundError:
        print("proxy.txt文件不存在，请先运行爬虫获取代理IP")
        return

    valid_count = 0
    total_count = 0

    while True:
        # 读取存放ip的文件
        ipinfo = proxyList.readline().strip()
        # 读到最后一行
        if len(ipinfo) == 0:
            break

        total_count += 1
        line = ipinfo.split('|')
        if len(line) < 2:
            continue

        ip = line[0]
        port = line[1]
        realip = ip + ':' + port

        # 得到验证码
        code = verifyProxy(realip)
        # 验证通过
        if code == 200:
            lock.acquire()
            print(f"---Success: {ip}:{port}")
            valid.write(ipinfo + "\n")
            valid_count += 1
            valid.flush()  # 立即写入文件
            lock.release()
        else:
            print(f"---Failure: {ip}:{port} (错误: {code})")

    proxyList.close()
    valid.close()
    print(f"验证完成！有效IP: {valid_count}/{total_count}")


def verifyProxy(ip):
    '''
    验证代理的有效性
    '''
    # 设置随机请求头
    headers = {
        'User-Agent': random.choice(user_agents)
    }
    url = "http://www.baidu.com"
    # 填写代理地址
    proxy = {'http': 'http://' + ip, 'https': 'https://' + ip}

    try:
        response = requests.get(url=url, proxies=proxy, timeout=5, headers=headers)
        return response.status_code
    except requests.exceptions.ConnectTimeout:
        return "连接超时"
    except requests.exceptions.ReadTimeout:
        return "读取超时"
    except requests.exceptions.ProxyError:
        return "代理错误"
    except requests.exceptions.ConnectionError:
        return "连接错误"
    except Exception as e:
        return f"其他错误: {str(e)}"


def useProxy():
    '''
    使用验证通过的代理IP访问目标网站
    '''
    # 获取可用ip池
    try:
        valid = open('valid.txt', 'r')
    except FileNotFoundError:
        print("valid.txt文件不存在，请先验证代理IP")
        return

    ips = []
    # 获取IP列表
    while True:
        # 读取存放ip的文件
        ipinfo = valid.readline().strip()
        # 读到最后一行
        if len(ipinfo) == 0:
            break
        line = ipinfo.split('|')
        if len(line) < 2:
            continue
        ip = line[0]
        port = line[1]
        realip = ip + ':' + port
        ips.append(realip)

    valid.close()

    if not ips:
        print("没有可用的代理IP")
        return

    print(f"找到 {len(ips)} 个可用代理IP")

    # 要抓取的目标网站地址
    targetUrl = "https://news.qq.com/"
    success_count = 0

    for i, proxyip in enumerate(ips[:10]):  # 只测试前10个
        print(f"测试第 {i + 1} 个代理: {proxyip}")
        try:
            response = requests.get(
                url=targetUrl,
                proxies={"http": "http://" + proxyip, "https": "https://" + proxyip},
                timeout=10,
                headers={'User-Agent': random.choice(user_agents)}
            )
            if response.status_code == 200:
                print(f"✅ 代理 {proxyip} 访问成功")
                success_count += 1
            else:
                print(f"❌ 代理 {proxyip} 访问失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ 代理 {proxyip} 异常: {e}")

    print(f"代理测试完成！成功: {success_count}/{min(10, len(ips))}")


if __name__ == '__main__':
    # 清空有效代理列表
    with open('valid.txt', 'w') as f:
        f.write("")

    print("开始验证代理IP有效性...")
    starttime = time.time()

    # 验证ip有效性 - 使用多线程
    all_thread = []
    thread_count = 10  # 减少线程数避免被封

    for i in range(thread_count):
        t = threading.Thread(target=verifyProxyList)
        all_thread.append(t)
        t.start()
        time.sleep(0.5)  # 延迟启动避免瞬时请求过多

    for t in all_thread:
        t.join()

    endtime = time.time()
    print(f"验证代理IP花费时间: {endtime - starttime:.2f}秒")

    # 使用验证通过的代理
    print("\n开始测试代理IP可用性...")
    useProxy()