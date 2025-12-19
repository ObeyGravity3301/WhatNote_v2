#!/usr/bin/env python3
"""
WhatNote V2 跨平台启动脚本
支持 Windows、Linux 和 macOS
"""

import os
import sys
import time
import signal
import subprocess
import threading
import platform
from pathlib import Path

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 服务配置
BACKEND_PORT = 8081
FRONTEND_PORT = 3000

# 平台检测
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MACOS = platform.system() == "Darwin"

# GPT-SoVITS 配置
# start_universal.py 位于 whatnote_v2/ 下
# PROJECT_ROOT 是 whatnote_v2/
# parent 是 whatnote/
# parent.parent 是 Projects/
# 所以 GPT-SoVITS 在 PROJECT_ROOT.parent.parent / "GPT-SoVITS"
GPT_SOVITS_DIR = (PROJECT_ROOT.parent.parent / "GPT-SoVITS").resolve()
GPT_SOVITS_PORT = 9880

class Colors:
    """终端颜色"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=Colors.ENDC):
    """打印彩色文本"""
    if IS_WINDOWS:
        # Windows 可能不支持颜色，使用普通文本
        print(text)
    else:
        print(f"{color}{text}{Colors.ENDC}")

def print_banner():
    """打印启动横幅"""
    system_name = "Windows" if IS_WINDOWS else ("macOS" if IS_MACOS else "Linux")
    banner = f"""
    ╔══════════════════════════════════════╗
    ║            WhatNote V2               ║
    ║     跨平台启动脚本 ({system_name})     ║
    ╚══════════════════════════════════════╝
    """
    print_colored(banner, Colors.BLUE + Colors.BOLD)

def kill_process_on_port(port):
    """终止占用指定端口的进程"""
    try:
        if IS_WINDOWS:
            # Windows 使用 netstat 和 taskkill
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        try:
                            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                            print_colored(f"[OK] 已终止端口 {port} 上的进程 (PID: {pid})", Colors.GREEN)
                        except:
                            pass
        else:
            # Unix/Linux/Mac 使用 lsof 和 kill
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        subprocess.run(['kill', '-9', pid], capture_output=True)
                    print_colored(f"[OK] 已终止端口 {port} 上的进程", Colors.GREEN)
            except:
                pass
    except Exception as e:
        print_colored(f"[Warning] 清理端口 {port} 时出错: {e}", Colors.YELLOW)

def get_gpt_sovits_python():
    """获取GPT-SoVITS虚拟环境中的Python路径"""
    if IS_WINDOWS:
        return GPT_SOVITS_DIR / "venv" / "Scripts" / "python.exe"
    else:
        return GPT_SOVITS_DIR / "venv" / "bin" / "python"

def start_gpt_sovits():
    """启动GPT-SoVITS服务"""
    if not GPT_SOVITS_DIR.exists():
        print_colored("[Warning] 未找到 GPT-SoVITS 目录，跳过启动", Colors.YELLOW)
        return None

    venv_python = get_gpt_sovits_python()
    if not venv_python.exists():
        print_colored("[Warning] 未找到 GPT-SoVITS 虚拟环境，跳过启动", Colors.YELLOW)
        return None

    print_colored("[Start] 启动 GPT-SoVITS 服务...", Colors.BLUE)
    
    try:
        cmd = [str(venv_python), 'api.py']
        
        # 设置环境变量
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        process = subprocess.Popen(
            cmd,
            cwd=GPT_SOVITS_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
            shell=False
        )
        
        print_colored(f"[OK] GPT-SoVITS 服务启动中 (端口: {GPT_SOVITS_PORT})", Colors.GREEN)
        return process
        
    except Exception as e:
        print_colored(f"[Error] GPT-SoVITS 启动失败: {e}", Colors.RED)
        return None

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_colored("[Error] 需要 Python 3.8 或更高版本", Colors.RED)
        return False
    print_colored(f"[OK] Python {version.major}.{version.minor}.{version.micro}", Colors.GREEN)
    return True

def check_node_version():
    """检查Node.js版本"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_colored(f"[OK] Node.js {version}", Colors.GREEN)
            return True
        else:
            print_colored("[Error] 未找到 Node.js", Colors.RED)
            return False
    except:
        print_colored("[Error] 未找到 Node.js", Colors.RED)
        return False

def get_python_executable():
    """获取Python可执行文件路径"""
    if IS_WINDOWS:
        return sys.executable
    else:
        return sys.executable

def get_venv_python():
    """获取虚拟环境中的Python路径"""
    if IS_WINDOWS:
        return PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    else:
        return PROJECT_ROOT / "venv" / "bin" / "python"

def setup_virtual_environment():
    """设置虚拟环境"""
    venv_path = PROJECT_ROOT / "venv"
    venv_python = get_venv_python()
    
    if venv_path.exists() and venv_python.exists():
        print_colored("[OK] 虚拟环境已存在", Colors.GREEN)
        return True
    
    try:
        print_colored("[Pkg] 创建虚拟环境...", Colors.BLUE)
        python_exe = get_python_executable()
        subprocess.run([python_exe, '-m', 'venv', 'venv'], 
                      cwd=PROJECT_ROOT, check=True, capture_output=True)
        
        # 升级pip
        print_colored("[Pkg] 升级pip...", Colors.BLUE)
        subprocess.run([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'], 
                      cwd=PROJECT_ROOT, check=True, capture_output=True)
        
        print_colored("[OK] 虚拟环境创建完成", Colors.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"[Error] 虚拟环境创建失败: {e}", Colors.RED)
        return False

def install_backend_deps():
    """安装后端依赖"""
    print_colored("[Pkg] 检查后端依赖...", Colors.BLUE)
    
    venv_python = get_venv_python()
    requirements_file = PROJECT_ROOT / "requirements.txt"
    
    if not requirements_file.exists():
        print_colored("[Error] 未找到 requirements.txt", Colors.RED)
        return False
    
    # 检查是否已经安装了主要依赖
    try:
        result = subprocess.run([str(venv_python), '-c', 'import fastapi, uvicorn'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print_colored("[OK] 后端依赖已安装", Colors.GREEN)
            return True
    except:
        pass
    
    # 需要安装依赖
    print_colored("[Pkg] 安装后端依赖...", Colors.BLUE)
    try:
        result = subprocess.run([str(venv_python), '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                               cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print_colored(f"[Error] 依赖安装失败:", Colors.RED)
            print(result.stderr)
            return False
        print_colored("[OK] 后端依赖安装完成", Colors.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"[Error] 后端依赖安装失败: {e}", Colors.RED)
        if e.stderr:
            print(e.stderr)
        return False

def install_frontend_deps():
    """安装前端依赖"""
    print_colored("[Pkg] 检查前端依赖...", Colors.BLUE)
    
    # 检查 node_modules 是否存在
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        print_colored("[OK] 前端依赖已安装", Colors.GREEN)
        return True
    
    try:
        # 根据平台选择npm命令
        npm_cmd = 'npm.cmd' if IS_WINDOWS else 'npm'
        subprocess.run([npm_cmd, 'install'], cwd=FRONTEND_DIR, check=True, capture_output=True)
        print_colored("[OK] 前端依赖安装完成", Colors.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"[Error] 前端依赖安装失败: {e}", Colors.RED)
        return False

def start_backend():
    """启动后端服务"""
    print_colored("[Start] 启动后端服务...", Colors.BLUE)
    
    try:
        venv_python = get_venv_python()
        cmd = [str(venv_python), 'run.py']
        
        # 设置环境变量
        env = os.environ.copy()
        
        process = subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
            shell=False
        )
        
        print_colored(f"[OK] 后端服务启动中 (端口: {BACKEND_PORT})", Colors.GREEN)
        return process
        
    except Exception as e:
        print_colored(f"[Error] 后端启动失败: {e}", Colors.RED)
        return None

def start_frontend():
    """启动前端服务"""
    print_colored("[Start] 启动前端服务...", Colors.BLUE)
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['BROWSER'] = 'none'  # 不自动打开浏览器
        env['PORT'] = str(FRONTEND_PORT)
        
        # 根据平台选择npm命令
        npm_cmd = 'npm.cmd' if IS_WINDOWS else 'npm'
        cmd = [npm_cmd, 'start']
        
        process = subprocess.Popen(
            cmd,
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
            shell=False
        )
        
        print_colored(f"[OK] 前端服务启动中 (端口: {FRONTEND_PORT})", Colors.GREEN)
        return process
        
    except Exception as e:
        print_colored(f"[Error] 前端启动失败: {e}", Colors.RED)
        return None

def monitor_process(process, name):
    """监控进程输出"""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f"[{name}] {output.strip()}")

def wait_for_services():
    """等待服务启动完成"""
    print_colored("[Wait] 等待服务启动完成...", Colors.YELLOW)
    
    # 等待后端
    for i in range(30):
        try:
            import requests
            response = requests.get(f'http://localhost:{BACKEND_PORT}/api/health', timeout=1)
            if response.status_code == 200:
                print_colored("[OK] 后端服务就绪", Colors.GREEN)
                break
        except:
            pass
        time.sleep(1)
    else:
        print_colored("[Warning] 后端服务启动超时", Colors.YELLOW)
    
    # 等待前端
    for i in range(60):
        try:
            import requests
            response = requests.get(f'http://localhost:{FRONTEND_PORT}', timeout=1)
            if response.status_code == 200:
                print_colored("[OK] 前端服务就绪", Colors.GREEN)
                break
        except:
            pass
        time.sleep(1)
    else:
        print_colored("[Warning] 前端服务启动超时", Colors.YELLOW)

def main():
    """主函数"""
    print_banner()
    
    # 环境检查
    print_colored("[Check] 检查运行环境...", Colors.BLUE)
    
    if not check_python_version():
        return False
    
    if not check_node_version():
        return False
    
    # 清理端口
    print_colored("[Clean] 清理端口...", Colors.BLUE)
    kill_process_on_port(BACKEND_PORT)
    kill_process_on_port(FRONTEND_PORT)
    kill_process_on_port(GPT_SOVITS_PORT)
    
    # 设置虚拟环境
    venv_path = PROJECT_ROOT / "venv"
    if not venv_path.exists():
        if not setup_virtual_environment():
            return False
    else:
        print_colored("[OK] 虚拟环境已存在", Colors.GREEN)
    
    # 安装依赖（如果虚拟环境可用）
    venv_python = get_venv_python()
    if venv_python.exists():
        if not install_backend_deps():
            print_colored("[Warning] 依赖安装失败，尝试使用现有环境", Colors.YELLOW)
    
    if not install_frontend_deps():
        return False
    
    # 启动服务
    gpt_sovits_process = start_gpt_sovits()
    
    backend_process = start_backend()
    if not backend_process:
        if gpt_sovits_process: gpt_sovits_process.terminate()
        return False
    
    time.sleep(2)  # 给后端一些启动时间
    
    frontend_process = start_frontend()
    if not frontend_process:
        backend_process.terminate()
        if gpt_sovits_process: gpt_sovits_process.terminate()
        return False
    
    # 启动监控线程
    backend_thread = threading.Thread(target=monitor_process, args=(backend_process, "Backend"))
    frontend_thread = threading.Thread(target=monitor_process, args=(frontend_process, "Frontend"))
    
    backend_thread.daemon = True
    frontend_thread.daemon = True
    
    backend_thread.start()
    frontend_thread.start()

    if gpt_sovits_process:
        gpt_thread = threading.Thread(target=monitor_process, args=(gpt_sovits_process, "GPT-SoVITS"))
        gpt_thread.daemon = True
        gpt_thread.start()
    
    # 等待服务就绪
    wait_for_services()
    
    # 显示访问信息
    print_colored("\n" + "="*50, Colors.GREEN)
    print_colored("[Success] WhatNote V2 启动成功!", Colors.GREEN + Colors.BOLD)
    print_colored("="*50, Colors.GREEN)
    print_colored(f"[FE] 前端界面: http://localhost:{FRONTEND_PORT}", Colors.BLUE)
    print_colored(f"[API] 后端API:  http://localhost:{BACKEND_PORT}", Colors.BLUE)
    print_colored(f"[TTS] TTS服务:  http://localhost:{GPT_SOVITS_PORT}", Colors.BLUE)
    print_colored(f"[Doc] API文档:  http://localhost:{BACKEND_PORT}/docs", Colors.BLUE)
    print_colored("="*50, Colors.GREEN)
    print_colored("[Tip] 按 Ctrl+C 停止所有服务", Colors.YELLOW)
    print_colored("="*50 + "\n", Colors.GREEN)
    
    try:
        # 等待用户中断
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print_colored("\n[Stop] 正在停止服务...", Colors.YELLOW)
        
        # 终止进程
        try:
            backend_process.terminate()
            frontend_process.terminate()
            if gpt_sovits_process: gpt_sovits_process.terminate()
            
            # 等待进程结束
            backend_process.wait(timeout=5)
            frontend_process.wait(timeout=5)
            if gpt_sovits_process: gpt_sovits_process.wait(timeout=5)
            
        except subprocess.TimeoutExpired:
            # 强制杀死进程
            backend_process.kill()
            frontend_process.kill()
            if gpt_sovits_process: gpt_sovits_process.kill()
        
        print_colored("[OK] 所有服务已停止", Colors.GREEN)
        return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print_colored("[Bye] 感谢使用 WhatNote V2!", Colors.BLUE)
        else:
            print_colored("[Error] 启动失败", Colors.RED)
            sys.exit(1)
    except Exception as e:
        print_colored(f"[Error] 启动脚本出错: {e}", Colors.RED)
        sys.exit(1)

