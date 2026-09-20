#!/usr/bin/env bash
# 一键启动 singing-expert（FastAPI 后端 + Vue 前端）
# 用法: ./start.sh        前台运行，Ctrl+C 一起退出
#       ./start.sh bg     后台运行，日志写到 .logs/

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV_PY="$BACKEND/.venv/bin/python"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

BACK_PORT=8000
FRONT_PORT=5173

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}[start]${NC} singing-expert 启动脚本"

# ---------- 1. 检查依赖 ----------
if [ ! -f "$VENV_PY" ]; then
  echo -e "${RED}[err]${NC} 未找到 backend/.venv，请先创建: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo -e "${YELLOW}[warn]${NC} 未找到 frontend/node_modules，执行 npm install..."
  (cd "$FRONTEND" && npm install)
fi

# ---------- 2. 端口检查 ----------
port_in_use() { lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; }

# 杀掉占用指定端口的进程（可选: 传 keep 则只提示不杀）
free_port() {
  local port=$1 name=$2
  if port_in_use "$port"; then
    local pid
    pid=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -n1)
    echo -e "${YELLOW}[warn]${NC} 端口 $port ($name) 已被占用 (pid=$pid)。"
    read -r -p "是否杀掉并重启? [Y/n] " ans < /dev/tty
    if [ "${ans:-Y}" != "${ans#[Yy]}" ]; then
      kill -9 "$pid" 2>/dev/null || true
      sleep 1
      echo -e "${GREEN}[ok]${NC} 已释放端口 $port"
    else
      echo -e "${YELLOW}[skip]${NC} 保留现有进程，跳过启动 $name"
      return 1
    fi
  fi
  return 0
}

# ---------- 3. 启动模式 ----------
MODE="${1:-fg}"
PIDS=()

cleanup() {
  echo -e "\n${YELLOW}[stop]${NC} 正在关闭服务..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null
  echo -e "${GREEN}[done]${NC} 已退出"
}
trap cleanup INT TERM EXIT

start_backend() {
  echo -e "${GREEN}[backend]${NC} 启动 FastAPI @ http://localhost:$BACK_PORT"
  (cd "$BACKEND" && exec "$VENV_PY" -m uvicorn main:app --reload --host 0.0.0.0 --port "$BACK_PORT") \
    >"$LOG_DIR/backend.log" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  echo "  pid=$pid  日志: $LOG_DIR/backend.log"
}

start_frontend() {
  echo -e "${GREEN}[frontend]${NC} 启动 Vite @ http://localhost:$FRONT_PORT"
  (cd "$FRONTEND" && exec npm run dev -- --port "$FRONT_PORT") \
    >"$LOG_DIR/frontend.log" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  echo "  pid=$pid  日志: $LOG_DIR/frontend.log"
}

# ---------- 4. 运行 ----------
free_port "$BACK_PORT"  "backend"  && start_backend
free_port "$FRONT_PORT" "frontend" && start_frontend

echo ""
echo -e "${GREEN}[ready]${NC} 启动完成"
echo "  后端 API:  http://localhost:$BACK_PORT/docs"
echo "  前端页面:  http://localhost:$FRONT_PORT"
echo ""

if [ "$MODE" = "bg" ]; then
  echo -e "${YELLOW}[bg]${NC} 后台运行中。日志: tail -f $LOG_DIR/*.log"
  echo "停止: kill ${PIDS[*]}"
  # 后台模式不阻塞，但需要解除 trap，否则脚本退出会把子进程杀掉
  trap - INT TERM EXIT
  exit 0
fi

# 前台模式：等待子进程
wait
