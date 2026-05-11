import os
import time
import subprocess
from seleniumbase import Driver

# 解析环境变量
raw_urls = os.environ.get('RENEW_URLS', '')
TARGET_URLS = [u.strip() for u in raw_urls.replace(';', ',').replace('\n', ',').split(',') if u.strip().startswith('http')]
PROXY_JSON = os.environ.get('PROXY_JSON', '')

EXTENSION_PATH = os.path.abspath(os.path.join(os.getcwd(), 'extensions', 'buster', 'unpacked'))

def start_proxy():
    print('[初始化] 准备 Hysteria2 代理配置...')
    with open('config.json', 'w') as f:
        f.write(PROXY_JSON)

    print('[Hysteria2] 启动中...')
    proxy_process = subprocess.Popen(
        ['hysteria', '-c', 'config.json'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(5)
    print('[Hysteria2] socks5: 127.0.0.1:10808 预计已就绪')
    return proxy_process

def main():
    if not TARGET_URLS:
        print('[错误] 未找到任何有效的续期链接！')
        return

    proxy_process = None
    if PROXY_JSON:
        proxy_process = start_proxy()

    print('[SeleniumBase] 启动 UC (Undetected) 模式以突破 Cloudflare...')
    
    # 启动隐形浏览器：加载代理和 Buster 插件
    driver = Driver(
        uc=True, 
        headless=False, # UC 模式配合 xvfb 必须用非无头模式才能完美伪装
        proxy="socks5://127.0.0.1:10808",
        extension_dir=EXTENSION_PATH
    )

    try:
        # 给 Buster 初始化时间，并关掉弹出的欢迎页
        time.sleep(3)
        handles = driver.window_handles
        for handle in handles:
            driver.switch_to.window(handle)
            if 'extension' in driver.current_url:
                driver.close()
        driver.switch_to.window(handles[0])

        for i, url in enumerate(TARGET_URLS):
            task_num = i + 1
            print(f'\n======================================================')
            print(f'[任务 {task_num}/{len(TARGET_URLS)}] 正在处理链接: {url}')
            print(f'======================================================')

            try:
                print(f'[任务 {task_num}] 访问续期链接并尝试绕过 Cloudflare...')
                # UC 模式专属打开网页方法，自带防屏蔽重连机制
                driver.uc_open_with_reconnect(url, reconnect_time=6)
                
                # 特殊指令：让 UC 模式自动接管并点击 Cloudflare 盾
                try:
                    driver.uc_gui_click_captcha()
                    time.sleep(4)
                except Exception:
                    pass # 如果没出现盾就跳过

                # 等待加载出蓝色按钮 (最多等20秒)
                print(f'[任务 {task_num} 交互] 查找蓝色的 "Renew server" 按钮...')
                driver.wait_for_element('//*[contains(text(), "Renew server")]', timeout=20)
                driver.click('//*[contains(text(), "Renew server")]')
                
                time.sleep(2)

                print(f'[任务 {task_num} 交互] 查找二次确认的紫色 Renew 按钮...')
                driver.click('//button[text()="Renew"]')
                print(f'[任务 {task_num} 交互] 验证码正式弹出！')

                time.sleep(3)

                # ==== 处理 reCAPTCHA 和 Buster ====
                try:
                    driver.switch_to_frame('iframe[title*="recaptcha challenge"]')
                    
                    driver.wait_for_element('#recaptcha-audio-button', timeout=6)
                    driver.click('#recaptcha-audio-button')
                    print(f'[任务 {task_num} 交互] 已切换到音频验证模式...')
                    
                    time.sleep(2)
                    
                    driver.click('.help-button-holder')
                    print(f'[任务 {task_num} 交互] 已呼叫 Buster 插件进行语音听写破解...')
                    
                    driver.switch_to_default_content()
                    
                    # 给 Buster 留足 25 秒的答题时间
                    time.sleep(25)
                except Exception as e:
                    print(f'[任务 {task_num} 警告] 语音破解流程未执行 (可能是CF未透传，或没出验证码): {e}')
                    driver.switch_to_default_content()

                # 截图保存结果
                screenshot_path = os.path.join('screenshots', f'4_final_result_{task_num}.png')
                driver.save_screenshot(screenshot_path)
                print(f'[任务 {task_num} 截图] 流程结束，请查看最终状态截图。')

            except Exception as e:
                print(f'[任务 {task_num} 错误] 发生异常中断: {e}')
                error_path = os.path.join('screenshots', f'error_crash_{task_num}.png')
                driver.save_screenshot(error_path)

    finally:
        driver.quit()
        if proxy_process:
            proxy_process.kill()
        print('\n[全部结束] 清理完毕。')

if __name__ == '__main__':
    main()
