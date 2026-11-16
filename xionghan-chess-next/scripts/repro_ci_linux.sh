#!/usr/bin/env bash
# 在 Linux（VMware / ubuntu-noble，最接近 CI 的 ubuntu-latest）里精确复现
# .github/workflows/ci.yml 的 test job，并打印 pytest 的 FAILED/ERROR 行。
#
# 前置（在 VM 里一次性做）：
#   ⚠️ 若主机通过 Clash 等代理/VPN 上 GitHub（中国网络常见），VM 的 NAT 不会继承该隧道，
#      必须让 VM 显式走主机代理：
#        HOST_IP=192.168.21.1        # 主机 VMnet8 的真实 IP（主机 ipconfig 查）
#        CLASH_PORT=7897             # Clash 的 HTTP 代理端口（你确认是 7897，非默认 7890）
#        export http_proxy=http://$HOST_IP:$CLASH_PORT
#        export https_proxy=http://$HOST_IP:$CLASH_PORT
#        git config --global http.proxy  $http_proxy
#        git config --global https.proxy $https_proxy
#        然后改用 HTTPS clone（比 SSH-over-proxy 简单）：
#          git clone https://github.com/Jinny168/xionghan-chess.git xionghan-chess
#          cd xionghan-chess && git lfs install && git lfs pull
#      pip 会自动读 https_proxy，无需额外配置。
#      若 Clash 是 TUN 模式，VM 流量可能已被主机接管，先 `curl -I https://github.com`
#      测一下，能通就不必设代理。
#   1) 克隆含 LFS（见上方代理说明）：
#                    git clone https://github.com/Jinny168/xionghan-chess.git xionghan-chess
#                    cd xionghan-chess && git lfs install && git lfs pull
#   2) 装 python3.12 + venv：
#                    sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
#   3) 装 Qt 离屏运行期系统库（noble）：
#                    sudo apt-get install -y libegl1 libgl1 libglib2.0-0 \
#                      libfontconfig1 libxkbcommon0 libdbus-1-3 libasound2t64 \
#                      libpulse-mainloop-glib0
#      （非 noble 把 libasound2t64 换成 libasound2）
#
# 用法： bash scripts/repro_ci_linux.sh
# 跑完看末尾「FAILED / ERROR」与「汇总」两段即可（把这两段贴回）。
set -uo pipefail

# 切到仓库根的 xionghan-chess-next 子树（ci.yml 的 working-directory）
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT/xionghan-chess-next"

export QT_QPA_PLATFORM=offscreen
export XDG_CONFIG_HOME="$(mktemp -d)/xdg-config"
export PYTHONUTF8=1
export PYTHONUNBUFFERED=1

# 选 python：优先 3.12
if command -v python3.12 >/dev/null 2>&1; then PY=python3.12
elif command -v python3 >/dev/null 2>&1; then PY=python3
else echo "::error:: 找不到 python3.12"; exit 1; fi

# 一次性建 venv + 装 lock 依赖（已存在则跳过）
if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/pip install -r requirements/lock/py312-dev.txt
fi
VENVPY=.venv/bin/python

# 装 Node.js 22（CI 用 22；对拍门禁缺 node 会误红，必须对齐；脚本其余部分依赖 node 可用）
if ! command -v node >/dev/null 2>&1 || [ "$(node --version | tr -d v | cut -d. -f1)" -lt 22 ]; then
  echo "=== 安装 Node.js 22（NodeSource）==="
  sudo apt-get install -y curl
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
echo "=== node 版本 ==="
node --version || echo "::error:: 缺 node（CI 用 22）"

# 门禁自检（镜像 CI：缺 node 必红 这条断言本身）
echo "=== 门禁自检 ==="
"$VENVPY" -m pytest tests/test_gate_integrity.py -q || echo "(gate-integrity 非零，见上)"

# 桌面壳体离屏冒烟（非致命，失败只打印不中止，目的是拿到主 pytest 失败行）
echo "=== 桌面冒烟 ==="
"$VENVPY" scripts/desktop_smoke.py >/tmp/smoke.log 2>&1 \
  || { echo "::smoke FAILED::"; tail -25 /tmp/smoke.log; }

# 重建派生产物 A→B→C（CI 在主 pytest 之前必跑；不跑则只读测试会误红/误绿）
echo "=== A gen_web_profiles --check ==="
"$VENVPY" scripts/gen_web_profiles.py --check
echo "=== B build_webapp_bundle ==="
"$VENVPY" scripts/build_webapp_bundle.py
echo "=== C build_webapp_bundle --check ==="
"$VENVPY" scripts/build_webapp_bundle.py --check

# 主 pytest（与 CI 逐字一致：不加 -m 默认值、--color=no、-rfEP）
echo "=== 主 pytest（CI 主门禁）==="
set -o pipefail
"$VENVPY" -m pytest tests/ -m "not slow" -q --color=no --durations=15 -rfEP 2>&1 | tee /tmp/pytest.log
rc=$?

echo ""
echo "================ FAILED / ERROR ================"
grep -aE "^(FAILED|ERROR) " /tmp/pytest.log | head -50 || echo "(无 FAILED/ERROR 行)"
echo "================ 汇总 ================"
grep -aE "^[0-9]+ (passed|failed)" /tmp/pytest.log | tail -3
echo "================ 建议回传 ================"
echo "把上面『FAILED / ERROR』与『汇总』两段贴回即可。"
exit $rc
