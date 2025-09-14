#!/usr/bin/env python3
"""
WhatNote V2 快速启动脚本
一键启动前端和后端服务
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 服务配置
BACKEND_PORT = 8081
FRONTEND_PORT = 3000

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
    print(f"{color}{text}{Colors.ENDC}")

def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════╗
    ║            WhatNote V2               ║
    ║         快速启动脚本                 ║
    ╚══════════════════════════════════════╝
    """
    print_colored(banner, Colors.BLUE + Colors.BOLD)

def kill_process_on_port(port):
    """终止占用指定端口的进程"""
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        try:
                            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                            print_colored(f"✓ 已终止端口 {port} 上的进程 (PID: {pid})", Colors.GREEN)
                        except:
                            pass
        else:  # Unix/Linux/Mac
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        subprocess.run(['kill', '-9', pid], capture_output=True)
                    print_colored(f"✓ 已终止端口 {port} 上的进程", Colors.GREEN)
            except:
                pass
    except Exception as e:
        print_colored(f"⚠ 清理端口 {port} 时出错: {e}", Colors.YELLOW)

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_colored("❌ 需要 Python 3.8 或更高版本", Colors.RED)
        return False
    print_colored(f"✓ Python {version.major}.{version.minor}.{version.micro}", Colors.GREEN)
    return True

def check_node_version():
    """检查Node.js版本"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_colored(f"✓ Node.js {version}", Colors.GREEN)
            return True
        else:
            print_colored("❌ 未找到 Node.js", Colors.RED)
            return False
    except:
        print_colored("❌ 未找到 Node.js", Colors.RED)
        return False

def install_backend_deps():
    """安装后端依赖"""
    print_colored("📦 检查后端依赖...", Colors.BLUE)
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      cwd=PROJECT_ROOT, check=True, capture_output=True)
        print_colored("✓ 后端依赖安装完成", Colors.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ 后端依赖安装失败: {e}", Colors.RED)
        return False

def install_frontend_deps():
    """安装前端依赖"""
    print_colored("📦 检查前端依赖...", Colors.BLUE)
    
    # 检查 node_modules 是否存在
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        print_colored("✓ 前端依赖已安装", Colors.GREEN)
        return True
    
    try:
        subprocess.run(['npm', 'install'], cwd=FRONTEND_DIR, check=True, capture_output=True)
        print_colored("✓ 前端依赖安装完成", Colors.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ 前端依赖安装失败: {e}", Colors.RED)
        return False

def start_backend():
    """启动后端服务"""
    print_colored("🚀 启动后端服务...", Colors.BLUE)
    
    # 添加后端目录到 Python 路径
    sys.path.insert(0, str(BACKEND_DIR))
    
    try:
        # 使用 uvicorn 启动后端
        cmd = [
            sys.executable, '-m', 'uvicorn', 
            'main:app', 
            '--host', '0.0.0.0',
            '--port', str(BACKEND_PORT),
            '--reload'
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        print_colored(f"✓ 后端服务启动中 (端口: {BACKEND_PORT})", Colors.GREEN)
        return process
        
    except Exception as e:
        print_colored(f"❌ 后端启动失败: {e}", Colors.RED)
        return None

def start_frontend():
    """启动前端服务"""
    print_colored("🚀 启动前端服务...", Colors.BLUE)
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['BROWSER'] = 'none'  # 不自动打开浏览器
        env['PORT'] = str(FRONTEND_PORT)
        
        # Windows 使用 npm.cmd
        npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
        cmd = [npm_cmd, 'start']
        
        process = subprocess.Popen(
            cmd,
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
            shell=True if os.name == 'nt' else False
        )
        
        print_colored(f"✓ 前端服务启动中 (端口: {FRONTEND_PORT})", Colors.GREEN)
        return process
        
    except Exception as e:
        print_colored(f"❌ 前端启动失败: {e}", Colors.RED)
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
    print_colored("⏳ 等待服务启动完成...", Colors.YELLOW)
    
    # 等待后端
    for i in range(30):
        try:
            # 尝试导入requests，如果没有就跳过检查
            try:
                import requests
                response = requests.get(f'http://localhost:{BACKEND_PORT}/', timeout=1)
                if response.status_code == 200:
                    print_colored("✓ 后端服务就绪", Colors.GREEN)
                    break
            except ImportError:
                # 如果没有requests，就简单等待
                time.sleep(5)
                print_colored("✓ 后端服务启动中（无法验证）", Colors.YELLOW)
                break
        except:
            pass
        time.sleep(1)
    else:
        print_colored("⚠ 后端服务启动超时", Colors.YELLOW)
    
    # 等待前端
    for i in range(60):
        try:
            try:
                import requests
                response = requests.get(f'http://localhost:{FRONTEND_PORT}', timeout=1)
                if response.status_code == 200:
                    print_colored("✓ 前端服务就绪", Colors.GREEN)
                    break
            except ImportError:
                time.sleep(10)
                print_colored("✓ 前端服务启动中（无法验证）", Colors.YELLOW)
                break
        except:
            pass
        time.sleep(1)
    else:
        print_colored("⚠ 前端服务启动超时", Colors.YELLOW)

def main():
    """主函数"""
    print_banner()
    
    # 环境检查
    print_colored("🔍 检查运行环境...", Colors.BLUE)
    
    if not check_python_version():
        return False
    
    if not check_node_version():
        return False
    
    # 清理端口
    print_colored("🧹 清理端口...", Colors.BLUE)
    kill_process_on_port(BACKEND_PORT)
    kill_process_on_port(FRONTEND_PORT)
    
    # 安装依赖
    if not install_backend_deps():
        return False
    
    if not install_frontend_deps():
        return False
    
    # 启动服务
    backend_process = start_backend()
    if not backend_process:
        return False
    
    time.sleep(2)  # 给后端一些启动时间
    
    frontend_process = start_frontend()
    if not frontend_process:
        backend_process.terminate()
        return False
    
    # 启动监控线程
    backend_thread = threading.Thread(target=monitor_process, args=(backend_process, "Backend"))
    frontend_thread = threading.Thread(target=monitor_process, args=(frontend_process, "Frontend"))
    
    backend_thread.daemon = True
    frontend_thread.daemon = True
    
    backend_thread.start()
    frontend_thread.start()
    
    # 等待服务就绪
    wait_for_services()
    
    # 显示访问信息
    print_colored("\n" + "="*50, Colors.GREEN)
    print_colored("🎉 WhatNote V2 启动成功!", Colors.GREEN + Colors.BOLD)
    print_colored("="*50, Colors.GREEN)
    print_colored(f"📱 前端界面: http://localhost:{FRONTEND_PORT}", Colors.BLUE)
    print_colored(f"🔧 后端API:  http://localhost:{BACKEND_PORT}", Colors.BLUE)
    print_colored(f"📊 API文档:  http://localhost:{BACKEND_PORT}/docs", Colors.BLUE)
    print_colored("="*50, Colors.GREEN)
    print_colored("💡 按 Ctrl+C 停止所有服务", Colors.YELLOW)
    print_colored("="*50 + "\n", Colors.GREEN)
    
    try:
        # 等待用户中断
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print_colored("\n🛑 正在停止服务...", Colors.YELLOW)
        
        # 终止进程
        try:
            backend_process.terminate()
            frontend_process.terminate()
            
            # 等待进程结束
            backend_process.wait(timeout=5)
            frontend_process.wait(timeout=5)
            
        except subprocess.TimeoutExpired:
            # 强制杀死进程
            backend_process.kill()
            frontend_process.kill()
        
        print_colored("✓ 所有服务已停止", Colors.GREEN)
        return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print_colored("👋 感谢使用 WhatNote V2!", Colors.BLUE)
        else:
            print_colored("❌ 启动失败", Colors.RED)
            sys.exit(1)
    except Exception as e:
        print_colored(f"❌ 启动脚本出错: {e}", Colors.RED)
        sys.exit(1)
