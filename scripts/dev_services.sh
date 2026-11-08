#!/usr/bin/env bash
# Local development services: project-isolated MySQL + portable Redis.
# Does not touch the existing MySQL service on 3306.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV="$ROOT/.dev"
MYSQL_DATA="$DEV/mysql/data"
MYSQL_RUN="$DEV/mysql/run"
MYSQL_LOG="$DEV/logs/mysql.err"
MYSQL_PID="$MYSQL_RUN/mysql.pid"
ROOT_PW_FILE="$DEV/mysql/root_password"

MYSQL_PORT="${MYSQL_PORT:-3307}"
MYSQL_BASEDIR="${MYSQL_BASEDIR:-C:/Program Files/MySQL/MySQL Server 9.4}"
MYSQLD="${MYSQLD:-$MYSQL_BASEDIR/bin/mysqld.exe}"
MYSQL_CLIENT="${MYSQL_CLIENT:-$MYSQL_BASEDIR/bin/mysql.exe}"
MYSQLADMIN="${MYSQLADMIN:-$MYSQL_BASEDIR/bin/mysqladmin.exe}"

REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-smarttest_redis_dev}"
REDIS_DIR="$DEV/redis"
REDIS_LOG="$DEV/logs/redis.log"
REDIS_SERVER="$ROOT/tools/redis/redis-server.exe"
REDIS_CLI="$ROOT/tools/redis/redis-cli.exe"

APP_DB_PASSWORD="${APP_DB_PASSWORD:-smarttest_dev_pw}"

mkdir -p "$MYSQL_DATA" "$MYSQL_RUN" "$DEV/logs" "$REDIS_DIR" "$ROOT/storage/projects" "$ROOT/storage/executions"

win_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1"
  else
    printf '%s\n' "$1"
  fi
}

mysql_root() {
  local args=("--protocol=tcp" "-h" "127.0.0.1" "-P" "$MYSQL_PORT" "-u" "root")
  if [[ -f "$ROOT_PW_FILE" ]]; then
    args+=("-p$(cat "$ROOT_PW_FILE")")
  fi
  "$MYSQL_CLIENT" "${args[@]}" "$@"
}

mysqladmin_root() {
  local args=("--protocol=tcp" "-h" "127.0.0.1" "-P" "$MYSQL_PORT" "-u" "root")
  if [[ -f "$ROOT_PW_FILE" ]]; then
    args+=("-p$(cat "$ROOT_PW_FILE")")
  fi
  "$MYSQLADMIN" "${args[@]}" "$@"
}

mysql_up() {
  mysqladmin_root ping >/dev/null 2>&1
}

redis_cli() {
  "$REDIS_CLI" -h 127.0.0.1 -p "$REDIS_PORT" -a "$REDIS_PASSWORD" "$@"
}

redis_up() {
  redis_cli ping >/dev/null 2>&1
}

start_mysql() {
  if [[ ! -x "$MYSQLD" ]]; then
    echo "[dev_services] ERROR: mysqld not found: $MYSQLD" >&2
    exit 1
  fi

  if [[ ! -d "$MYSQL_DATA/mysql" ]]; then
    echo "[dev_services] initializing project MySQL data dir (first run)..."
    "$MYSQLD" \
      --initialize-insecure \
      --basedir="$MYSQL_BASEDIR" \
      --datadir="$(win_path "$MYSQL_DATA")" \
      --console >"$MYSQL_LOG" 2>&1 || {
        echo "[dev_services] MySQL initialization failed. Last log lines:" >&2
        tail -40 "$MYSQL_LOG" >&2 || true
        exit 1
      }
  fi

  if mysql_up; then
    echo "[dev_services] MySQL already running on 127.0.0.1:$MYSQL_PORT"
  else
    echo "[dev_services] starting MySQL on 127.0.0.1:$MYSQL_PORT ..."
    nohup "$MYSQLD" \
      --basedir="$MYSQL_BASEDIR" \
      --datadir="$(win_path "$MYSQL_DATA")" \
      --port="$MYSQL_PORT" \
      --bind-address=127.0.0.1 \
      --mysqlx=0 \
      --character-set-server=utf8mb4 \
      --collation-server=utf8mb4_0900_ai_ci \
      --default-time-zone=+00:00 \
      --max-allowed-packet=64M \
      --log-error="$(win_path "$MYSQL_LOG")" \
      --pid-file="$(win_path "$MYSQL_PID")" \
      >/dev/null 2>&1 &
    for _ in $(seq 1 60); do
      sleep 1
      if mysql_up; then break; fi
    done
    if ! mysql_up; then
      echo "[dev_services] MySQL did not become ready. Last log lines:" >&2
      tail -60 "$MYSQL_LOG" >&2 || true
      exit 1
    fi
  fi

  # First run: root has an empty password. Set one and store it locally.
  if [[ ! -f "$ROOT_PW_FILE" ]]; then
    local root_pw
    root_pw="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
    "$MYSQL_CLIENT" --protocol=tcp -h 127.0.0.1 -P "$MYSQL_PORT" -u root \
      -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${root_pw}';" || {
        echo "[dev_services] ERROR: could not set root password. If this instance already" >&2
        echo "  has a password, write it to $ROOT_PW_FILE or delete .dev/mysql/data." >&2
        exit 1
      }
    printf '%s' "$root_pw" >"$ROOT_PW_FILE"
    chmod 600 "$ROOT_PW_FILE" 2>/dev/null || true
    echo "[dev_services] stored local MySQL root password in .dev/mysql/root_password"
  fi

  mysql_root <<SQL
CREATE DATABASE IF NOT EXISTS \`smarttest\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS \`smarttest_test\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'smarttest'@'%' IDENTIFIED BY '${APP_DB_PASSWORD}';
ALTER USER 'smarttest'@'%' IDENTIFIED BY '${APP_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`smarttest\`.* TO 'smarttest'@'%';
GRANT ALL PRIVILEGES ON \`smarttest_test\`.* TO 'smarttest'@'%';
FLUSH PRIVILEGES;
SQL
  echo "[dev_services] MySQL ready: 127.0.0.1:$MYSQL_PORT (db=smarttest, user=smarttest)"
}

start_redis() {
  if [[ ! -x "$REDIS_SERVER" ]]; then
    echo "[dev_services] Redis binary missing, downloading ..."
    bash "$ROOT/scripts/fetch_redis.sh"
  fi

  if redis_up; then
    echo "[dev_services] Redis already running on 127.0.0.1:$REDIS_PORT"
    return
  fi

  echo "[dev_services] starting Redis on 127.0.0.1:$REDIS_PORT ..."
  nohup "$REDIS_SERVER" \
    --bind 127.0.0.1 \
    --port "$REDIS_PORT" \
    --requirepass "$REDIS_PASSWORD" \
    --save "" \
    --appendonly no \
    --protected-mode yes \
    --dir "$(win_path "$REDIS_DIR")" \
    >"$REDIS_LOG" 2>&1 &
  for _ in $(seq 1 30); do
    sleep 1
    if redis_up; then break; fi
  done
  if ! redis_up; then
    echo "[dev_services] Redis did not become ready. Last log lines:" >&2
    tail -40 "$REDIS_LOG" >&2 || true
    exit 1
  fi
  echo "[dev_services] Redis ready: 127.0.0.1:$REDIS_PORT"
}

stop_services() {
  if redis_up; then
    echo "[dev_services] stopping Redis ..."
    redis_cli shutdown nosave >/dev/null 2>&1 || true
  fi
  if mysql_up; then
    echo "[dev_services] stopping MySQL ..."
    mysqladmin_root shutdown >/dev/null 2>&1 || true
    for _ in $(seq 1 30); do
      sleep 1
      if ! mysql_up; then break; fi
    done
  fi
  echo "[dev_services] stopped"
}

status_services() {
  local rc=0
  if mysql_up; then
    echo "MySQL:  UP   127.0.0.1:$MYSQL_PORT (project data: .dev/mysql/data)"
  else
    echo "MySQL:  DOWN 127.0.0.1:$MYSQL_PORT"
    rc=1
  fi
  if redis_up; then
    echo "Redis:  UP   127.0.0.1:$REDIS_PORT"
  else
    echo "Redis:  DOWN 127.0.0.1:$REDIS_PORT"
    rc=1
  fi
  return "$rc"
}

case "${1:-}" in
  start)
    start_mysql
    start_redis
    ;;
  stop)
    stop_services
    ;;
  restart)
    stop_services
    start_mysql
    start_redis
    ;;
  status)
    status_services
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
