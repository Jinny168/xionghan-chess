#!/bin/bash
# 雄汉象棋 Linux 部署检查脚本
# 用途：自动检查部署环境和配置

echo "========================================"
echo "  雄汉象棋 - Linux 部署环境检查"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查结果计数
PASS=0
FAIL=0
WARN=0

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../.."

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

# 1. 检查操作系统
echo "[1/8] 检查操作系统..."
if [ -f /etc/os-release ]; then
    OS_NAME=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')
    check_pass "操作系统: $OS_NAME"
else
    check_warn "无法检测操作系统"
fi
echo ""

# 2. 检查 Docker
echo "[2/8] 检查 Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    check_pass "Docker 已安装: $DOCKER_VERSION"
    
    # 检查 Docker 服务状态
    if systemctl is-active --quiet docker; then
        check_pass "Docker 服务正在运行"
    else
        check_fail "Docker 服务未运行，执行: sudo systemctl start docker"
    fi
else
    check_fail "Docker 未安装"
    echo "   安装命令: curl -fsSL https://get.docker.com | sh"
fi
echo ""

# 3. 检查 Docker Compose
echo "[3/8] 检查 Docker Compose..."
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    check_pass "Docker Compose 已安装: $COMPOSE_VERSION"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    check_pass "Docker Compose (plugin) 已安装: $COMPOSE_VERSION"
else
    check_fail "Docker Compose 未安装"
    echo "   安装命令: sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    echo "   然后执行: sudo chmod +x /usr/local/bin/docker-compose"
fi
echo ""

# 4. 检查项目文件
echo "[4/8] 检查项目文件..."

if [ -f "$PROJECT_DIR/config/docker-compose.yml" ]; then
    check_pass "docker-compose.yml 存在"
else
    check_fail "docker-compose.yml 不存在"
fi

if [ -f "$PROJECT_DIR/config/Dockerfile" ]; then
    check_pass "Dockerfile 存在"
else
    check_fail "Dockerfile 不存在"
fi

if [ -f "$PROJECT_DIR/config/.env" ]; then
    check_pass ".env 配置文件存在"
    
    # 检查是否使用默认密码
    if grep -q "REDIS_PASSWORD=XionghanChess2024" "$PROJECT_DIR/config/.env"; then
        check_warn "检测到使用默认密码，建议修改"
    fi
else
    check_fail ".env 配置文件不存在"
    echo "   执行: cp config/.env.example config/.env 并编辑"
fi
echo ""

# 5. 检查端口占用
echo "[5/8] 检查端口占用..."
PORTS=(80 443 5000 6379)
for port in "${PORTS[@]}"; do
    if ss -tlnp | grep -q ":$port "; then
        check_warn "端口 $port 已被占用"
    else
        check_pass "端口 $port 可用"
    fi
done
echo ""

# 6. 检查防火墙
echo "[6/8] 检查防火墙..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status | head -1)
    if echo "$UFW_STATUS" | grep -q "active"; then
        check_pass "防火墙已启用: $UFW_STATUS"
        
        # 检查必要端口是否开放
        for port in 80 5000; do
            if sudo ufw status | grep -q "$port/tcp.*ALLOW"; then
                check_pass "端口 $port 已开放"
            else
                check_warn "端口 $port 未开放，执行: sudo ufw allow $port/tcp"
            fi
        done
    else
        check_warn "防火墙未启用（开发环境可以，生产环境建议启用）"
    fi
else
    check_warn "ufw 防火墙未安装"
fi
echo ""

# 7. 检查磁盘空间
echo "[7/8] 检查磁盘空间..."
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "磁盘使用率: ${DISK_USAGE}%（正常）"
elif [ "$DISK_USAGE" -lt 90 ]; then
    check_warn "磁盘使用率: ${DISK_USAGE}%（偏高）"
else
    check_fail "磁盘使用率: ${DISK_USAGE}%（过高，需要清理）"
fi
echo ""

# 8. 检查内存
echo "[8/8] 检查内存..."
TOTAL_MEM=$(free -m | awk '/^Mem:/ {print $2}')
if [ "$TOTAL_MEM" -ge 3800 ]; then
    check_pass "总内存: ${TOTAL_MEM}MB（充足）"
elif [ "$TOTAL_MEM" -ge 1900 ]; then
    check_warn "总内存: ${TOTAL_MEM}MB（建议增加到 4GB）"
else
    check_fail "总内存: ${TOTAL_MEM}MB（不足，至少需要 2GB）"
fi
echo ""

# 总结
echo "========================================"
echo "  检查结果汇总"
echo "========================================"
echo -e "${GREEN}通过: $PASS${NC}"
echo -e "${YELLOW}警告: $WARN${NC}"
echo -e "${RED}失败: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ 环境检查通过，可以开始部署！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 确认 config/.env 配置正确"
    echo "  2. 执行: docker-compose -f config/docker-compose.yml up -d"
    echo "  3. 查看日志: docker-compose -f config/docker-compose.yml logs -f"
else
    echo -e "${RED}✗ 发现 $FAIL 个问题，请先解决后再部署${NC}"
fi
echo ""

# 如果所有检查通过，询问是否启动
if [ $FAIL -eq 0 ] && [ $WARN -eq 0 ]; then
    read -p "是否立即启动服务？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "启动服务..."
        cd "$PROJECT_DIR"
        docker-compose -f config/docker-compose.yml up -d
        echo ""
        echo "查看服务状态："
        docker-compose -f config/docker-compose.yml ps
        echo ""
        echo "访问地址：http://$(hostname -I | awk '{print $1}')"
    fi
fi
