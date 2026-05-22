#!/bin/bash
# Web 版本一键部署脚本（简化版）

set -e

echo "========================================"
echo "  雄汉象棋 Web 版 - Docker 部署"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo -e "${YELLOW}提示：本脚本将部署 Web 版本的雄汉象棋${NC}"
echo ""

# 检查 .env 文件
if [ ! -f docker/.env ]; then
    echo "创建配置文件..."
    cp docker/.env.example docker/.env
    echo -e "${GREEN}已创建 docker/.env 文件${NC}"
fi

# 启动服务
echo ""
echo "正在启动服务..."
docker-compose -f docker/docker-compose.yml up -d

echo ""
echo -e "${GREEN}服务启动完成！${NC}"
echo ""

# 等待服务启动
sleep 5

# 显示状态
echo "服务状态："
docker-compose -f docker/docker-compose.yml ps
echo ""

# 获取 IP
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "========================================"
echo -e "${GREEN}  部署成功！${NC}"
echo "========================================"
echo ""
echo "访问地址："
echo "  - http://${IP_ADDRESS}"
echo "  - http://${IP_ADDRESS}:5000"
echo ""
echo "管理命令："
echo "  - 查看日志: docker-compose -f docker/docker-compose.yml logs -f"
echo "  - 停止服务: docker-compose -f docker/docker-compose.yml down"
echo "  - 重启服务: docker-compose -f docker/docker-compose.yml restart"
echo ""
