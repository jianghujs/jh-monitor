#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ES_CONFIG_PATH="${ROOT_DIR}/data/es.json"
FILEBEAT_CONFIG_PATH="${FILEBEAT_CONFIG_PATH:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

ES_URL="${ES_URL:-}"
ES_USER="${ES_USER:-}"
ES_PASS="${ES_PASS:-}"
HOST_ID=""
HOST_ID_INDEX=""
MONTH_TEXT=""
AUTO_CONFIRM="0"
AUTO_DELETE="1"

EXPECTED_TEMPLATE_NAME="host-debian-system-status-template"
EXPECTED_TEMPLATE_PRIORITY="500"

show_info() {
  echo "[fix-debian-es] $*"
}

show_error() {
  echo "[fix-debian-es] ERROR: $*" >&2
}

fail() {
  show_error "$*"
  exit 1
}

prompt_yes_no() {
  local message="$1"
  local default_value="${2:-N}"
  local input=""

  if [ "$AUTO_CONFIRM" = "1" ]; then
    return 0
  fi

  if [ "$default_value" = "Y" ]; then
    read -r -p "${message} [Y/n]: " input
    input="${input:-Y}"
  else
    read -r -p "${message} [y/N]: " input
    input="${input:-N}"
  fi

  case "$input" in
    y|Y|yes|YES)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

usage() {
  cat <<'EOF'
用法:
  bash fix_debian_system_status_template.sh --host-id-index h-dev04-dc207-axw3 [--month 2026.04]
  bash fix_debian_system_status_template.sh --host-id H_Dev04@DC207_AxW3 [--month 2026.04]

说明:
  1. 补齐 ES 模板 host-debian-system-status-template
  2. 检查指定主机的 system-status 数据流是否错误绑定到 filebeat 宿主模板
  3. 执行确认后，如目标数据流已存在，则自动删除该数据流，等待 filebeat 重新写入
  4. 默认优先从客户端 filebeat 配置读取 ES 连接信息和 host_id_index

参数:
  --host-id            主机 host_id，会自动转换成 host_id_index
  --host-id-index      直接指定 host_id_index
  --month              数据流月份，支持 YYYY.MM 或 YYYY-MM，默认当前月份
  --filebeat-config    filebeat 配置路径，默认优先尝试 /etc/filebeat/filebeat.yml，再尝试 /etc/filebeat.yml
  --es-url             ES 地址，例如 http://127.0.0.1:9200
  --username           ES 用户名
  --password           ES 密码
  --yes                跳过总确认
  --delete-data-stream 保留兼容参数，当前版本默认自动删除已有目标数据流
  -h, --help           查看帮助
EOF
}

normalize_host_id_for_index() {
  local raw="$1"
  local normalized=""
  normalized="$(printf "%s" "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
  if [ -z "$normalized" ]; then
    normalized="host"
  fi
  printf "%s" "$normalized"
}

normalize_month() {
  local raw="${1:-}"
  if [ -z "$raw" ]; then
    date '+%Y.%m'
    return 0
  fi

  raw="${raw//-/.}"
  if printf "%s" "$raw" | grep -Eq '^[0-9]{4}\.[0-9]{2}$'; then
    printf "%s" "$raw"
    return 0
  fi

  fail "月份格式不正确，请使用 YYYY.MM 或 YYYY-MM"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --host-id)
      HOST_ID="${2:-}"
      shift 2
      ;;
    --host-id-index)
      HOST_ID_INDEX="${2:-}"
      shift 2
      ;;
    --month)
      MONTH_TEXT="${2:-}"
      shift 2
      ;;
    --filebeat-config)
      FILEBEAT_CONFIG_PATH="${2:-}"
      shift 2
      ;;
    --es-url)
      ES_URL="${2:-}"
      shift 2
      ;;
    --username)
      ES_USER="${2:-}"
      shift 2
      ;;
    --password)
      ES_PASS="${2:-}"
      shift 2
      ;;
    --yes)
      AUTO_CONFIRM="1"
      shift
      ;;
    --delete-data-stream)
      AUTO_DELETE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "不支持的参数: $1"
      ;;
  esac
done

if [ -n "$HOST_ID" ] && [ -z "$HOST_ID_INDEX" ]; then
  HOST_ID_INDEX="$(normalize_host_id_for_index "$HOST_ID")"
fi

resolve_filebeat_config_path() {
  if [ -n "$FILEBEAT_CONFIG_PATH" ] && [ -f "$FILEBEAT_CONFIG_PATH" ]; then
    printf "%s" "$FILEBEAT_CONFIG_PATH"
    return 0
  fi

  if [ -f /etc/filebeat/filebeat.yml ]; then
    printf "%s" "/etc/filebeat/filebeat.yml"
    return 0
  fi

  if [ -f /etc/filebeat.yml ]; then
    printf "%s" "/etc/filebeat.yml"
    return 0
  fi

  return 1
}

read_filebeat_config_values() {
  local config_path="$1"
  "$PYTHON_BIN" - <<'PY' "$config_path"
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fp:
    text = fp.read()

def pick(pattern):
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()

host_value = pick(r'^\s*hosts:\s*\[\s*"([^"]+)"')
user_value = pick(r'^\s*username:\s*"([^"]*)"')
pass_value = pick(r'^\s*password:\s*"([^"]*)"')
index_value = pick(r'^\s*-\s*index:\s*"host-debian-(.+)-system-status-%\{\+yyyy\.MM\}"')

print(host_value)
print(user_value)
print(pass_value)
print(index_value)
PY
}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail "未找到 ${PYTHON_BIN}"
fi

if [ -z "$ES_URL" ] || [ -z "$ES_USER" ] || [ -z "$ES_PASS" ] || [ -z "$HOST_ID_INDEX" ]; then
  if FILEBEAT_CONFIG_PATH_RESOLVED="$(resolve_filebeat_config_path)"; then
    readarray -t FILEBEAT_CONF < <(read_filebeat_config_values "$FILEBEAT_CONFIG_PATH_RESOLVED")
    if [ -z "$ES_URL" ] && [ -n "${FILEBEAT_CONF[0]:-}" ]; then
      ES_URL="http://${FILEBEAT_CONF[0]}"
    fi
    if [ -z "$ES_USER" ] && [ -n "${FILEBEAT_CONF[1]:-}" ]; then
      ES_USER="${FILEBEAT_CONF[1]}"
    fi
    if [ -z "$ES_PASS" ] && [ -n "${FILEBEAT_CONF[2]:-}" ]; then
      ES_PASS="${FILEBEAT_CONF[2]}"
    fi
    if [ -z "$HOST_ID_INDEX" ] && [ -n "${FILEBEAT_CONF[3]:-}" ]; then
      HOST_ID_INDEX="${FILEBEAT_CONF[3]}"
    fi
  fi
fi

if [ -z "$ES_URL" ] || [ -z "$ES_USER" ] || [ -z "$ES_PASS" ]; then
  if [ ! -f "$ES_CONFIG_PATH" ]; then
    fail "未找到 filebeat 配置，且未通过参数传入 ES 连接信息；项目 ES 配置也不存在: $ES_CONFIG_PATH"
  fi

  readarray -t ES_CONF < <(
    "$PYTHON_BIN" - <<'PY' "$ES_CONFIG_PATH"
import json
import sys

config_path = sys.argv[1]
with open(config_path, "r", encoding="utf-8") as fp:
    config = json.load(fp)

hosts = config.get("hosts", []) or []
host = "127.0.0.1"
port = 9200
scheme = "http"
if hosts:
    host = str(hosts[0].get("host", host) or host)
    port = int(hosts[0].get("port", port) or port)
    scheme = str(hosts[0].get("scheme", scheme) or scheme)

print(f"{scheme}://{host}:{port}")
print(str(config.get("username", "") or ""))
print(str(config.get("password", "") or ""))
PY
  )

  ES_URL="${ES_URL:-${ES_CONF[0]}}"
  ES_USER="${ES_USER:-${ES_CONF[1]}}"
  ES_PASS="${ES_PASS:-${ES_CONF[2]}}"
fi

[ -n "$HOST_ID_INDEX" ] || fail "未能自动识别 host_id_index，请通过 --host-id 或 --host-id-index 指定"
MONTH_TEXT="$(normalize_month "$MONTH_TEXT")"
TARGET_DATA_STREAM="host-debian-${HOST_ID_INDEX}-system-status-${MONTH_TEXT}"
WRONG_TEMPLATE_NAME="host-debian-${HOST_ID_INDEX}-logs"

[ -n "$ES_URL" ] || fail "ES_URL 不能为空"
[ -n "$ES_USER" ] || fail "ES 用户名不能为空"
[ -n "$ES_PASS" ] || fail "ES 密码不能为空"

command -v curl >/dev/null 2>&1 || fail "未找到 curl"

curl_json() {
  local path="$1"
  local method="${2:-GET}"
  local body="${3:-}"
  if [ -n "$body" ]; then
    curl -sS -u "${ES_USER}:${ES_PASS}" -X "$method" "${ES_URL}${path}" \
      -H "Content-Type: application/json" -d "$body"
  else
    curl -sS -u "${ES_USER}:${ES_PASS}" -X "$method" "${ES_URL}${path}"
  fi
}

render_template_body() {
  cat <<'JSON'
{
  "index_patterns": ["host-debian-*-system-status-*"],
  "priority": 500,
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "dynamic": true,
      "dynamic_templates": [
        {
          "size_bytes_as_double": {
            "path_match": "*.size_bytes",
            "match_mapping_type": "long",
            "mapping": { "type": "double" }
          }
        },
        {
          "total_size_bytes_as_double": {
            "path_match": "*.total_size_bytes",
            "match_mapping_type": "long",
            "mapping": { "type": "double" }
          }
        },
        {
          "last_backup_size_bytes_as_double": {
            "path_match": "*.last_backup_size_bytes",
            "match_mapping_type": "long",
            "mapping": { "type": "double" }
          }
        }
      ],
      "properties": {
        "@timestamp": { "type": "date" },
        "host": {
          "dynamic": true,
          "properties": {
            "host_id": { "type": "keyword" },
            "host_name": { "type": "keyword" },
            "host_ip": { "type": "ip" },
            "host_group": { "type": "keyword" },
            "host_status": { "type": "keyword" },
            "system_type": { "type": "keyword" }
          }
        },
        "system": {
          "dynamic": true,
          "properties": {
            "cpu": { "type": "float" },
            "memory": { "type": "float" },
            "load": {
              "dynamic": true,
              "properties": {
                "pro": { "type": "float" },
                "one": { "type": "float" },
                "five": { "type": "float" },
                "fifteen": { "type": "float" }
              }
            },
            "disks": { "type": "nested" }
          }
        },
        "site": { "type": "nested" },
        "jianghujs": { "type": "nested" },
        "docker": { "type": "nested" },
        "mysql": {
          "type": "object",
          "dynamic": true,
          "properties": {
            "total_size_bytes": { "type": "double" },
            "tables": {
              "type": "object",
              "dynamic": true,
              "properties": {
                "size_bytes": { "type": "double" }
              }
            }
          }
        },
        "backup": {
          "type": "object",
          "dynamic": true
        },
        "lsync": {
          "type": "object",
          "dynamic": true
        },
        "rsync": { "type": "nested" },
        "collector": {
          "dynamic": true,
          "properties": {
            "source": { "type": "keyword" },
            "version": { "type": "keyword" }
          }
        },
        "add_time": {
          "type": "date",
          "format": "yyyy-MM-dd HH:mm:ss||strict_date_optional_time"
        },
        "add_timestamp": { "type": "double" }
      }
    }
  },
  "data_stream": {}
}
JSON
}

show_info "-----------------------"
show_info "准备修复 Debian system-status 数据流模板"
show_info "步骤1/5: 检查 ES 连通性"
show_info "步骤2/5: 创建或更新模板 ${EXPECTED_TEMPLATE_NAME}"
show_info "步骤3/5: 检查目标数据流 ${TARGET_DATA_STREAM}"
show_info "步骤4/5: 如目标数据流已存在，则自动删除该数据流"
show_info "步骤5/5: 输出修复结果与后续操作建议"
show_info "-----------------------"
show_info "ES地址: ${ES_URL}"
if [ -n "${FILEBEAT_CONFIG_PATH_RESOLVED:-}" ]; then
  show_info "filebeat配置: ${FILEBEAT_CONFIG_PATH_RESOLVED}"
else
  show_info "filebeat配置: 未使用，当前通过参数或 data/es.json 获取 ES 信息"
fi
show_info "目标主机: ${HOST_ID_INDEX}"
show_info "目标月份: ${MONTH_TEXT}"
show_info "目标数据流: ${TARGET_DATA_STREAM}"
show_info "预期模板: ${EXPECTED_TEMPLATE_NAME}"
show_info "旧宿主模板: ${WRONG_TEMPLATE_NAME}"
show_info "删除策略: 已确认执行后自动删除已有目标数据流"

if ! prompt_yes_no "确认开始执行以上修复步骤吗？" "Y"; then
  show_info "已取消执行"
  exit 0
fi

show_info "开始执行..."

show_info "-----------------------"
show_info "步骤1/5: 检查 ES 连通性"
ES_ROOT_JSON="$(curl_json "/" "GET")"
printf '%s' "$ES_ROOT_JSON" | "$PYTHON_BIN" -c '
import json
import sys
data = json.load(sys.stdin)
print(json.dumps({
    "cluster_name": data.get("cluster_name"),
    "version": (data.get("version") or {}).get("number"),
    "tagline": data.get("tagline")
}, ensure_ascii=False, indent=2))
'
show_info "ES 连通性检查通过"

show_info "-----------------------"
show_info "步骤2/5: 创建或更新模板 ${EXPECTED_TEMPLATE_NAME}"
TEMPLATE_BODY="$(render_template_body)"
PUT_TEMPLATE_JSON="$(curl_json "/_index_template/${EXPECTED_TEMPLATE_NAME}" "PUT" "$TEMPLATE_BODY")"
printf '%s' "$PUT_TEMPLATE_JSON" | "$PYTHON_BIN" -c '
import json
import sys
print(json.dumps(json.load(sys.stdin), ensure_ascii=False, indent=2))
'
show_info "模板写入完成"

show_info "再次确认模板内容"
GET_TEMPLATE_JSON="$(curl_json "/_index_template/${EXPECTED_TEMPLATE_NAME}" "GET")"
printf '%s' "$GET_TEMPLATE_JSON" | "$PYTHON_BIN" -c '
import json
import sys
data = json.load(sys.stdin)
templates = data.get("index_templates", []) or []
item = templates[0].get("index_template", {}) if templates else {}
mapping = item.get("template", {}).get("mappings", {})
mysql_props = ((mapping.get("properties", {}) or {}).get("mysql", {}).get("properties", {}) or {})
tables_props = ((mysql_props.get("tables", {}) or {}).get("properties", {}) or {})
print(json.dumps({
    "template_exists": bool(templates),
    "index_patterns": item.get("index_patterns", []),
    "priority": item.get("priority"),
    "mysql.total_size_bytes": (mysql_props.get("total_size_bytes") or {}).get("type"),
    "mysql.tables.size_bytes": (tables_props.get("size_bytes") or {}).get("type")
}, ensure_ascii=False, indent=2))
'
show_info "模板检查完成"

show_info "-----------------------"
show_info "步骤3/5: 检查目标数据流 ${TARGET_DATA_STREAM}"
DATA_STREAM_JSON="$(curl_json "/_data_stream/${TARGET_DATA_STREAM}" "GET" || true)"

if printf '%s' "$DATA_STREAM_JSON" | grep -q '"status"[[:space:]]*:[[:space:]]*404'; then
  show_info "当前未找到目标数据流，无需删除旧数据流"
  show_info "后续只需在客户端重启 filebeat，即可按新模板自动创建"
  show_info "-----------------------"
  show_info "处理完成"
  show_info "后续建议:"
  show_info "1. 在客户端执行 systemctl restart filebeat"
  show_info "2. 再次检查 /_data_stream/${TARGET_DATA_STREAM}"
  exit 0
fi

printf '%s' "$DATA_STREAM_JSON" | "$PYTHON_BIN" -c '
import json
import sys
data = json.load(sys.stdin)
streams = data.get("data_streams", []) or []
if not streams:
    print(json.dumps({"exists": False}, ensure_ascii=False, indent=2))
    raise SystemExit(0)
item = streams[0]
indices = item.get("indices", []) or []
print(json.dumps({
    "exists": True,
    "name": item.get("name"),
    "template": item.get("template"),
    "status": item.get("status"),
    "write_index": indices[-1].get("index_name") if indices else ""
}, ensure_ascii=False, indent=2))
'

CURRENT_TEMPLATE="$(printf '%s' "$DATA_STREAM_JSON" | "$PYTHON_BIN" -c '
import json
import sys
data = json.load(sys.stdin)
streams = data.get("data_streams", []) or []
print((streams[0].get("template") if streams else "") or "")
')"

show_info "-----------------------"
show_info "步骤4/5: 自动删除已有目标数据流"
if [ "$CURRENT_TEMPLATE" = "$EXPECTED_TEMPLATE_NAME" ]; then
  show_info "当前数据流已绑定正确模板，但已有 backing index 可能仍沿用旧状态"
  show_info "为确保按最新模板重新创建，继续删除当前数据流"
else
  show_info "检测到数据流当前绑定模板不是预期模板: ${CURRENT_TEMPLATE}"
  show_info "这通常说明它是在正确模板创建前被 filebeat 宿主模板抢先创建出来的"
  show_info "删除后，待客户端重新写入时会按新模板重新创建"
fi

if [ "$AUTO_DELETE" = "1" ]; then
  DELETE_JSON="$(curl_json "/_data_stream/${TARGET_DATA_STREAM}" "DELETE")"
  printf '%s' "$DELETE_JSON" | "$PYTHON_BIN" -c '
import json
import sys
print(json.dumps(json.load(sys.stdin), ensure_ascii=False, indent=2))
'
  show_info "目标数据流已删除"
else
  show_info "已跳过删除数据流，请确认停掉客户端 filebeat 后再手工处理"
fi

show_info "-----------------------"
show_info "步骤5/5: 输出最终结果"
FINAL_TEMPLATE_JSON="$(curl_json "/_index_template/${EXPECTED_TEMPLATE_NAME}" "GET")"
printf '%s' "$FINAL_TEMPLATE_JSON" | "$PYTHON_BIN" -c '
import json
import sys
data = json.load(sys.stdin)
templates = data.get("index_templates", []) or []
item = templates[0].get("index_template", {}) if templates else {}
print(json.dumps({
    "template": "host-debian-system-status-template",
    "exists": bool(templates),
    "priority": item.get("priority"),
    "index_patterns": item.get("index_patterns", [])
}, ensure_ascii=False, indent=2))
'

show_info "-----------------------"
show_info "处理完成"
show_info "后续建议:"
show_info "1. 到客户端机器执行 systemctl restart filebeat"
show_info "2. 再检查数据流是否已绑定到 ${EXPECTED_TEMPLATE_NAME}"
show_info "3. 如仍有 size_bytes 类型冲突，再把客户端采集脚本里的 size_bytes 统一改成 int"
