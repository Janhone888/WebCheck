import webbrowser
import time
import urllib.request
import urllib.error
import socket
import ssl
import threading
import queue
import os
from datetime import datetime

# 您提供的网址列表
urls = [
    "https://f1.352343.cc",
    "https://f2.352343.cc",
    "https://f3.352343.cc",
    "https://fn1.352343.cc",
    "https://fn2.352343.cc",
    "https://fn3.352343.cc",
    "https://fn3.344233.cc",
    "https://fn1.344233.cc",
    "https://fn2.344233.cc",
    "https://f3.453521.xyz",
    "https://fn4.233235.xyz",  # 故意添加错误协议测试
    "https://fn6.757866.xyz",
    "https://f2.453521.xyz",
    "https://f1.453521.xyz",
    "https://f1.170809.xyz",
    "https://f2.170809.xyz",
    "https://f3.170809.xyz",
    "https://fn4.476579.xyz",
    "https://fn7.476579.xyz",
    "https://fn5.233235.xyz",
    "https://fn6.233235.xyz",
    "https://fn7.476579.xyz",
    "https://fn8.476579.xyz",
    "https://fn9.476579.xyz",
    "https://fn4.757866.xyz",
    "https://fn5.757866.xyz",
    "https://fn6.757866.xyz",
    "https://fn4.476579.xyz",
    "https://fn5.476579.xyz",
    "https://fn6.476579.xyz",
    "https://fn3.476579.xyz",
    "https://fn1.476579.xyz",
    "https://fn2.476579.xyz",
    "https://fn1.767887.xyz",
    "https://fn2.767887.xyz",
    "https://fn3.767887.xyz",
    "https://fn1.595780.xyz",
    "https://fn2.595780.xyz",
    "https://fn3.595780.xyz",
    "https://fn1.233235.xyz",
    "https://fn2.233235.xyz",
    "https://fn3.233235.xyz",
    "https://fn4.170809.xyz",
    "https://fn5.170809.xyz",
    "https://fn6.170809.xyz",
    "https://fn1.170809.xyz",
    "https://fn2.170809.xyz",
    "https://fn3.170809.xyz",
    "https://fn2.170203.xyz",
    "https://fn3.170203.xyz",
    "https://fn1.170203.xyz"
]

# 移除重复URL
unique_urls = []
for url in urls:
    if url not in unique_urls:
        unique_urls.append(url)

print(f"原始URL数量: {len(urls)}")
print(f"去重后URL数量: {len(unique_urls)}")
print("开始智能打开网站...")

# 创建不验证SSL证书的上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 统计变量
successful = 0
failed = 0
skipped = 0

# 创建队列用于多线程
url_queue = queue.Queue()
result_queue = queue.Queue()

# 填充队列
for url in unique_urls:
    url_queue.put(url)


# 线程工作函数
def check_website(thread_id):
    while not url_queue.empty():
        try:
            url = url_queue.get_nowait()
        except queue.Empty:
            break

        # 验证URL格式
        if not url.startswith("http"):
            result_queue.put(("error", url, "无效协议"))
            continue

        # 尝试连接网站
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            req = urllib.request.Request(url, headers=headers)

            # 使用更短的超时时间
            with urllib.request.urlopen(req, timeout=3, context=ssl_context) as response:
                status = response.getcode()

                # 仅当网站可用时才返回结果
                if 200 <= status < 400:
                    result_queue.put(("success", url, status))
                else:
                    result_queue.put(("fail", url, f"HTTP错误: {status}"))

        except Exception as e:
            # 处理各种可能的错误
            error_type = type(e).__name__
            error_msg = str(e)

            if isinstance(e, urllib.error.HTTPError):
                result_queue.put(("fail", url, f"HTTP错误: {e.code}"))
            elif isinstance(e, urllib.error.URLError):
                result_queue.put(("fail", url, f"URL错误: {e.reason}"))
            elif isinstance(e, socket.timeout):
                result_queue.put(("fail", url, "连接超时"))
            elif isinstance(e, socket.gaierror):
                result_queue.put(("fail", url, "域名解析失败"))
            elif "CERTIFICATE_VERIFY_FAILED" in error_msg:
                result_queue.put(("fail", url, "SSL证书验证失败"))
            else:
                result_queue.put(("fail", url, f"错误: {error_type}"))

        finally:
            url_queue.task_done()


# 创建并启动线程
num_threads = min(20, len(unique_urls))  # 最多20个线程
threads = []
print(f"启动 {num_threads} 个线程并行检查网站...")

for i in range(num_threads):
    thread = threading.Thread(target=check_website, args=(i,))
    thread.daemon = True
    thread.start()
    threads.append(thread)

# 主线程处理结果并打开网站
print("开始处理结果并打开可用网站...")
print("=" * 80)
print(f"{'状态':<8} | {'网址':<35} | {'详细信息'}")
print("-" * 80)

# 实时处理结果
processed = 0
start_time = time.time()

while processed < len(unique_urls):
    try:
        # 等待结果，最多等待5秒
        result = result_queue.get(timeout=5)
        status, url, detail = result
        processed += 1

        # 显示结果
        status_display = {
            "success": "✓ 成功",
            "fail": "✗ 失败",
            "error": "⚠ 错误"
        }.get(status, status)

        print(f"{status_display:<8} | {url[:35]:<35} | {detail}")

        # 如果网站可用，立即打开
        if status == "success":
            webbrowser.open_new_tab(url)
            successful += 1
        elif status == "fail":
            failed += 1
        else:  # error
            skipped += 1

        # 每处理10个网站显示一次进度
        if processed % 10 == 0:
            elapsed = time.time() - start_time
            remaining = (len(unique_urls) - processed) * (elapsed / processed)
            print(f"\n进度: {processed}/{len(unique_urls)} | 耗时: {elapsed:.1f}秒 | 预计剩余: {remaining:.1f}秒")
            print("-" * 80)

    except queue.Empty:
        # 检查是否有线程仍在工作
        active_threads = sum(1 for t in threads if t.is_alive())
        if active_threads == 0 and url_queue.empty():
            break

# 等待所有线程完成
for thread in threads:
    thread.join(timeout=1)

# 最终统计
elapsed_time = time.time() - start_time
print("\n" + "=" * 80)
print(f"处理完成! 总耗时: {elapsed_time:.2f}秒")
print(f"  成功打开: {successful} 个网站")
print(f"  失败网站: {failed} 个")
print(f"  跳过网站: {skipped} 个")
print("=" * 80)

# 提供失败网站报告
if failed > 0 or skipped > 0:
    report_choice = input("\n是否要生成失败网站报告? (y/n): ").lower()
    if report_choice == 'y':
        # 创建结果文件夹
        results_dir = "website_reports"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(results_dir, f"website_failures_{timestamp}.txt")

        # 重新检查失败网站（单线程，详细检查）
        print("\n重新检查失败网站，请稍候...")
        detailed_failures = []

        for url in unique_urls:
            # 跳过成功网站
            if url in [r[1] for r in list(result_queue.queue) if r[0] == "success"]:
                continue

            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                req = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
                    status = response.getcode()
                    detailed_failures.append((url, f"HTTP状态码: {status}"))
            except Exception as e:
                detailed_failures.append((url, f"错误: {type(e).__name__} - {str(e)}"))

        # 写入报告
        with open(filename, "w", encoding="utf-8") as f:
            f.write("网站故障诊断报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总网站数: {len(unique_urls)}\n")
            f.write(f"成功网站: {successful}\n")
            f.write(f"失败网站: {len(detailed_failures)}\n\n")

            f.write("===== 失败网站详情 =====\n")
            for url, reason in detailed_failures:
                f.write(f"{url}\n")
                f.write(f"原因: {reason}\n\n")

        print(f"报告已保存至: {filename}")
        print(f"您可以在 '{results_dir}' 文件夹中找到它")

print("\n程序结束。已打开的网站保留在浏览器中。")