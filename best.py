import webbrowser
import time
import urllib.request
import socket
import ssl
import os
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# 优化后的配置参数
MAX_THREADS = 30  # 增加并行线程数
TIMEOUT = 1.5  # 减少超时时间
OPEN_DELAY = 0.1  # 减少打开间隔
REPORT_DIR = "website_reports"
URLS_FILE = "website_list.txt"


def deduplicate_urls(urls):
    seen = set()
    return [url for url in urls if not (url in seen or seen.add(url))]


def load_urls_from_file(file_path):
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    if not line.startswith(('http://', 'https://')):
                        line = 'https://' + line
                    urls.append(line)
        return urls
    except FileNotFoundError:
        print(f"错误: URL文件 {file_path} 不存在。")
        return []
    except Exception as e:
        print(f"读取URL文件时出错: {str(e)}")
        return []


def check_website(url):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Connection": "close"  # 显式关闭连接避免资源占用
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        # 使用更高效的socket操作
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl_context) as response:
            if 200 <= response.status < 400:
                return ("success", url, response.status)
            return ("fail", url, f"HTTP {response.status}")

    except urllib.error.HTTPError as e:
        return ("fail", url, f"HTTP {e.code}")
    except (urllib.error.URLError, socket.timeout, socket.gaierror) as e:
        return ("fail", url, str(e))
    except Exception as e:
        return ("error", url, str(e))


def display_status(status, url, detail):
    status_symbols = {"success": "✓", "fail": "✗", "error": "⚠"}
    symbol = status_symbols.get(status, "?")
    print(f"{symbol} {status.upper():<7} | {url[:45]:<45} | {detail}")


def open_urls(urls):
    for url in urls:
        webbrowser.open_new_tab(url)
        time.sleep(OPEN_DELAY)


def generate_report(results, total_count):
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(REPORT_DIR, f"website_report_{timestamp}.txt")

    success_urls = [url for status, url, _ in results if status == "success"]
    fail_urls = [(url, detail) for status, url, detail in results if status == "fail"]
    error_urls = [(url, detail) for status, url, detail in results if status == "error"]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("网站可用性检查报告\n")
        f.write(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总网站数: {total_count}\n")
        f.write(f"成功网站: {len(success_urls)}\n")
        f.write(f"失败网站: {len(fail_urls)}\n")
        f.write(f"错误网站: {len(error_urls)}\n\n")

        f.write("===== 成功网站 =====\n")
        f.write("\n".join(success_urls))

        f.write("\n\n===== 失败网站 =====\n")
        for url, detail in fail_urls:
            f.write(f"{url}\n原因: {detail}\n")

        f.write("\n===== 错误网站 =====\n")
        for url, detail in error_urls:
            f.write(f"{url}\n原因: {detail}\n")

    return filename


def main():
    print("网站批量检查工具 v3.0 (优化版)")
    print("=" * 80)

    # 从文件加载URL
    urls = load_urls_from_file(URLS_FILE)
    if not urls:
        print("没有可用的URL，程序退出。")
        return

    # 去重处理
    unique_urls = deduplicate_urls(urls)
    total = len(unique_urls)
    print(f"加载URL数量: {len(urls)} | 去重后数量: {total}")
    print(f"优化配置: 线程数={MAX_THREADS}, 超时={TIMEOUT}秒")

    start_time = time.time()
    results = []
    success_urls = []

    print(f"\n启动最多 {MAX_THREADS} 个线程并行检查网站...")
    print("-" * 80)

    # 使用更高效的线程池处理
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(check_website, url): url for url in unique_urls}

        completed = 0
        last_update = time.time()

        while futures:
            # 使用wait提高响应速度
            done, not_done = wait(futures, timeout=0.1, return_when=FIRST_COMPLETED)

            for future in done:
                url = futures[future]
                try:
                    result = future.result()
                    status, url, detail = result
                    results.append(result)

                    display_status(status, url, detail)

                    if status == "success":
                        success_urls.append(url)

                    completed += 1

                    # 更频繁地更新进度（每完成一个任务都可能更新）
                    current_time = time.time()
                    if current_time - last_update > 0.5 or completed == total:
                        elapsed = current_time - start_time
                        print(
                            f"进度: {completed}/{total} | 耗时: {elapsed:.1f}秒 | 速度: {completed / max(1, elapsed):.1f}个/秒")
                        print("-" * 80)
                        last_update = current_time

                except Exception as e:
                    error_result = ("error", url, str(e))
                    results.append(error_result)
                    display_status("error", url, str(e))

                del futures[future]

    # 最终统计
    elapsed_time = time.time() - start_time
    success_count = len(success_urls)
    fail_count = sum(1 for r in results if r[0] == "fail")
    error_count = sum(1 for r in results if r[0] == "error")

    print("\n" + "=" * 80)
    print(f"处理完成! 总耗时: {elapsed_time:.2f}秒")
    print(f"  成功网站: {success_count} 个")
    print(f"  失败网站: {fail_count} 个")
    print(f"  错误网站: {error_count} 个")
    print("=" * 80)

    # 询问是否打开可用网站
    if success_urls:
        choice = input("\n是否要在浏览器中打开可用网站? (y/n): ").strip().lower()
        if choice == 'y':
            print(f"正在打开 {success_count} 个网站...")
            open_urls(success_urls)
            print("网站已打开!")

    # 生成报告
    report_file = generate_report(results, total)
    print(f"\n报告已保存至: {report_file}")

    print("\n程序结束。感谢使用!")


if __name__ == "__main__":
    main()