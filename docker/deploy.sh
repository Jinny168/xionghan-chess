#!/bin/bash
# 雄汉象棋 Linux 一键部署脚本（简化版）
# 适合小白用户，自动完成所有步骤

set -e  # 遇到错误立即退出

echo "========================================"
echo "  雄汉象棋 - Linux 一键部署"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}提示：本脚本将自动完成以下操作：${NC}"
echo "  1. 检查系统环境"
echo "  2. 安装 Docker 和 Docker Compose"
echo "  3. 配置环境变量"
echo "  4. 启动服务"
echo ""

read -p "是否继续？(y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi
echo ""

# ==================== 步骤 1：检查系统 ====================
echo -e "${BLUE}[步骤 1/5] 检查系统环境...${NC}"

# 检查是否为 root 或 sudo 权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}警告：建议使用 sudo 运行此脚本${NC}"
    read -p "是否使用 sudo 重新运行？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo bash "$0"
        exit $?
    fi
fi

# 检查操作系统
if [ -f /etc/os-release ]; then
    OS_ID=$(grep ^ID= /etc/os-release | cut -d= -f2)
    echo "检测到操作系统: $OS_ID"
else
    echo -e "${RED}错误：无法检测操作系统${NC}"
    exit 1
fi

# 检查架构
ARCH=$(uname -m)
echo "系统架构: $ARCH"
echo ""

# ==================== 步骤 2：安装 Docker ====================
echo -e "${BLUE}[步骤 2/5] 安装 Docker...${NC}"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker 已安装${NC}"
    docker --version
else
    echo "正在安装 Docker..."
    
    if [ "$OS_ID" = "ubuntu" ] || [ "$OS_ID" = "debian" ]; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    elif [ "$OS_ID" = "centos" ] || [ "$OS_ID" = "rhel" ]; then
        # CentOS/RHEL
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io
    else
        echo -e "${RED}不支持的操作系统: $OS_ID${NC}"
        echo "请手动安装 Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    echo -e "${GREEN}Docker 安装完成${NC}"
    docker --version
fi

# 启动 Docker 服务
sudo systemctl enable docker
sudo systemctl start docker

# 添加当前用户到 docker 组
sudo usermod -aG docker $USER
echo -e "${YELLOW}注意：需要重新登录才能使 docker 组生效${NC}"
echo ""

# ==================== 步骤 3：安装 Docker Compose ====================
echo -e "${BLUE}[步骤 3/5] 安装 Docker Compose...${NC}"

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}Docker Compose 已安装${NC}"
    docker-compose --version
elif docker compose version &> /dev/null; then
    echo -e "${GREEN}Docker Compose (plugin) 已安装${NC}"
    docker compose version
else
    echo "正在安装 Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose 安装完成${NC}"
    docker-compose --version
fi
echo ""

# ==================== 步骤 4：配置环境变量 ====================
echo -e "${BLUE}[步骤 4/5] 配置环境变量...${NC}"

if [ ! -f .env ]; then
    echo "创建 .env 配置文件..."
    cp .env.example .env
    
    # 生成随机密码
    RANDOM_PASSWORD=$(openssl rand -base64 12 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 12)
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${RANDOM_PASSWORD}/" .env
    
    echo -e "${GREEN}已创建 .env 文件${NC}"
    echo -e "${YELLOW}Redis 密码: ${RANDOM_PASSWORD}${NC}"
    echo "请妥善保存此密码！"
else
    echo -e "${GREEN}.env 文件已存在${NC}"
fi

# 显示当前配置
echo ""
echo "当前配置："
grep -v "^#" .env | grep -v "^$"
echo ""

read -p "是否需要修改配置？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "使用 nano 编辑器打开 .env 文件"
    echo "修改完成后按 Ctrl+O 保存，Ctrl+X 退出"
    read -p "按回车键继续..."
    nano .env
fi
echo ""

# ==================== 步骤 5：启动服务 ====================
echo -e "${BLUE}[步骤 5/5] 启动服务...${NC}"

echo "正在拉取镜像并启动服务..."
docker-compose up -d

echo ""
echo -e "${GREEN}服务启动完成！${NC}"
echo ""

# 等待服务启动
echo "等待服务初始化..."
sleep 5

# 检查服务状态
echo "服务状态："
docker-compose ps
echo ""

# 获取 IP 地址
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "========================================"
echo -e "${GREEN}  部署成功！${NC}"
echo "========================================"
echo ""
echo "访问地址："
echo "  - HTTP: http://${IP_ADDRESS}"
echo "  - 直接访问: http://${IP_ADDRESS}:5000"
echo ""
echo "管理命令："
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo "  - 更新代码: git pull && docker-compose up -d --build"
echo ""
echo "重要提示："
echo "  - Redis 密码已保存到 .env 文件"
echo "  - 请妥善保管，不要泄露"
echo "  - 建议定期备份数据"
echo ""

# 询问是否查看日志
read -p "是否查看实时日志？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "按 Ctrl+C 退出日志查看"
    echo ""
    docker-compose logs -f
fi
