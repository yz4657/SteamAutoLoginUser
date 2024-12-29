import os
import subprocess
import winreg as reg
import psutil
import time
import vdf
import winreg


# 获取 Steam 安装路径
def get_steam_install_path():
    try:
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(reg_key, "SteamPath")
        winreg.CloseKey(reg_key)
        if os.path.exists(steam_path):
            return steam_path
        else:
            print("Steam 安装路径无效。")
            return None
    except FileNotFoundError:
        print("未找到 Steam 注册表项。")
        return None


# 获取 loginusers.vdf 路径
def get_loginusers_vdf_path(steam_path):
    if steam_path:
        return os.path.join(steam_path, "config", "loginusers.vdf")
    return None


# 检查 Steam 是否已运行
def is_steam_running():
    """检查 Steam 是否正在运行"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'].lower() == 'steam.exe':
            return True
    return False


# 结束 Steam 进程（先使用 taskkill 尝试，如果失败使用第二种方法）
def kill_steam_processes():
    """结束 Steam 客户端和相关服务进程"""
    try:
        subprocess.run(['taskkill', '/f', '/im', 'steam.exe'], check=True)
        subprocess.run(['taskkill', '/f', '/im', 'SteamService.exe'], check=True)
        print("Steam processes terminated successfully (first attempt).")
    except subprocess.CalledProcessError:
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == 'steam.exe' or proc.info['name'].lower() == 'SteamService.exe':
                    proc.kill()  # 强制杀死进程
            print("Steam processes terminated successfully (second attempt).")
        except Exception as e:
            print(f"无法关闭 Steam 进程: {e}")


# 修改注册表的 AutoLoginUser 值
def modify_registry(account_name):
    """修改注册表以设置自动登录账号"""
    try:
        registry_key = reg.HKEY_CURRENT_USER
        sub_key = r"SOFTWARE\Valve\Steam"
        key = reg.OpenKey(registry_key, sub_key, 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(key, "AutoLoginUser", 0, reg.REG_SZ, account_name)
        reg.CloseKey(key)
        print(f"AutoLoginUser registry set to {account_name}.")
    except Exception as e:
        print(f"Failed to modify registry: {e}")


# 启动 Steam 客户端（不等待 Steam 完全启动）
def start_steam(steam_path):
    """启动 Steam 客户端"""
    try:
        process = subprocess.Popen([steam_path])  # 使用实际的 Steam 路径
        print("Steam 客户端已启动。")
    except subprocess.CalledProcessError:
        print("Failed to start Steam. Check if the path is correct.")


# 从 loginusers.vdf 文件中读取账号信息
def get_steam_accounts(loginusers_vdf_path):
    try:
        with open(loginusers_vdf_path, 'r', encoding='utf-8') as file:
            data = vdf.parse(file)
            if "users" in data:
                return data["users"]
            else:
                print("文件内容格式不符合预期。")
                return {}
    except FileNotFoundError:
        print(f"Error: {loginusers_vdf_path} 文件未找到。")
        return {}
    except Exception as e:
        print(f"读取或解析文件时出错: {e}")
        return {}

# 查找最近使用的账号
def find_most_recent_account(data, get_key, get_value):
    for steam_id, account_info in data.items():
        if account_info.get(get_key) == get_value:
            return steam_id, account_info
    return None, None


# 主要逻辑
def main():
    try:
        # 获取 Steam 安装路径
        steam_install_path = get_steam_install_path()
        if not steam_install_path:
            print("无法获取 Steam 安装路径。")
            return

        # 获取 loginusers.vdf 路径
        loginusers_vdf_path = get_loginusers_vdf_path(steam_install_path)
        if not loginusers_vdf_path:
            print("无法获取 loginusers.vdf 文件路径。")
            return

        # 获取所有账户信息
        accounts = get_steam_accounts(loginusers_vdf_path)
        if not accounts:
            print("没有找到任何 Steam 账户。")
            return

        # 检查 Steam 是否已经在运行
        if not is_steam_running():
            # 如果 Steam 没有运行，启动 Steam 并登录最近使用的账号
            steam_id, account_info = find_most_recent_account(accounts, 'MostRecent', "1")
            if account_info:
                print(f"Steam 未启动，启动 Steam 登入账号 {account_info['AccountName']}")
                start_steam(os.path.join(steam_install_path, 'Steam.exe'))
        else:
            # 如果 Steam 已经启动，切换账号
            print("Steam 已经启动，关闭 Steam 并准备切换账号...")
            kill_steam_processes()
            time.sleep(3)  # 等待进程完全结束

            # 获取下一个账号并切换
            steam_id, current_account = find_most_recent_account(accounts, 'MostRecent', "0")
            if current_account:
                modify_registry(current_account['AccountName'])
                print(f"切换账号为: {current_account['AccountName']}")
                # 重新启动 Steam 客户端
                start_steam(os.path.join(steam_install_path, 'Steam.exe'))

    except Exception as e:
        print(f"程序发生错误: {e}")


if __name__ == "__main__":
    main()
