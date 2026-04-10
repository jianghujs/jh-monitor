#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ES_CONFIG_PATH="${ROOT_DIR}/data/es.json"
PYTHON_BIN="${PYTHON_BIN:-python3}"

HOST_ID=""
HOST_ID_INDEX=""
DATA_STREAM_PATTERN=""

log() {
  echo "[check-debian-es] $*"
}

fail() {
  echo "[check-debian-es] ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法:
  bash check_debian_es_mapping.sh [--host-id H_debian_My0b] [--host-id-index h-debian-my0b]

说明:
  - 默认检查所有 host-debian-*-system-status-* 数据流
  - 指定 --host-id 或 --host-id-index 时，会只检查对应主机
  - 读取当前项目的 data/es.json 连接 ES
EOF
}

normalize_host_id_for_index() {
  local raw="$1"
  local normalized
  normalized="$(printf "%s" "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
  if [ -z "$normalized" ]; then
    normalized="host"
  fi
  printf "%s" "$normalized"
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

if [ -n "$HOST_ID_INDEX" ]; then
  DATA_STREAM_PATTERN="host-debian-${HOST_ID_INDEX}-system-status-*"
else
  DATA_STREAM_PATTERN="host-debian-*-system-status-*"
fi

if [ ! -f "$ES_CONFIG_PATH" ]; then
  fail "未找到 ES 配置文件: $ES_CONFIG_PATH"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail "未找到 python3"
fi

readarray -t ES_CONF < <(
  "$PYTHON_BIN" - <<'PY' "$ES_CONFIG_PATH"
import json
import sys

config_path = sys.argv[1]
with open(config_path, "r") as fp:
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

ES_ADDR="${ES_CONF[0]}"
ES_USER="${ES_CONF[1]}"
ES_PASS="${ES_CONF[2]}"

curl_json() {
  local path="$1"
  local method="${2:-GET}"
  local data="${3:-}"

  if [ -n "$data" ]; then
    curl -sS -u "${ES_USER}:${ES_PASS}" -X "$method" "${ES_ADDR}${path}" \
      -H "Content-Type: application/json" -d "$data"
  else
    curl -sS -u "${ES_USER}:${ES_PASS}" -X "$method" "${ES_ADDR}${path}"
  fi
}

log "步骤1/4: 检查 ES 连通性"
curl_json "/" | "$PYTHON_BIN" -c '
import json
import sys

data = json.load(sys.stdin)
print(json.dumps({
    "name": data.get("name"),
    "cluster_name": data.get("cluster_name"),
    "version": (data.get("version") or {}).get("number"),
}, ensure_ascii=False, indent=2))
'

log "步骤2/4: 检查模板 host-debian-system-status-template"
TEMPLATE_JSON="$(curl_json "/_index_template/host-debian-system-status-template")"
printf '%s' "$TEMPLATE_JSON" | "$PYTHON_BIN" -c '
import json
import sys

data = json.load(sys.stdin)
templates = data.get("index_templates", []) or []
if not templates:
    print(json.dumps({
        "template_exists": False,
        "message": "未找到 host-debian-system-status-template"
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0)

item = templates[0].get("index_template", {})
mapping = item.get("template", {}).get("mappings", {})
props = mapping.get("properties", {})
mysql_props = ((props.get("mysql") or {}).get("properties") or {})
tables_props = ((mysql_props.get("tables") or {}).get("properties") or {})
dynamic_templates = mapping.get("dynamic_templates", [])

print(json.dumps({
    "template_exists": True,
    "index_patterns": item.get("index_patterns", []),
    "priority": item.get("priority"),
    "mysql.total_size_bytes": (mysql_props.get("total_size_bytes") or {}).get("type"),
    "mysql.tables.size_bytes": (tables_props.get("size_bytes") or {}).get("type"),
    "dynamic_templates": dynamic_templates,
}, ensure_ascii=False, indent=2))
'

log "步骤3/4: 检查数据流 pattern=${DATA_STREAM_PATTERN}"
DATA_STREAM_JSON="$(curl_json "/_data_stream/${DATA_STREAM_PATTERN}")"
printf '%s' "$DATA_STREAM_JSON" | "$PYTHON_BIN" -c '
import json
import sys

data = json.load(sys.stdin)
streams = data.get("data_streams", []) or []
if not streams:
    print(json.dumps({
        "data_stream_count": 0,
        "message": "未找到匹配的数据流"
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0)

summary = []
for item in streams:
    indices = item.get("indices", []) or []
    summary.append({
        "name": item.get("name"),
        "generation": item.get("generation"),
        "backing_index_count": len(indices),
        "write_index": indices[-1].get("index_name") if indices else "",
        "template": item.get("template"),
    })

print(json.dumps({
    "data_stream_count": len(streams),
    "data_streams": summary,
}, ensure_ascii=False, indent=2))
'

log "步骤4/4: 检查字段映射和最新文档"
printf '%s' "$DATA_STREAM_JSON" | "$PYTHON_BIN" -c '
import json
import subprocess
import sys

es_addr, es_user, es_pass = sys.argv[1:4]
data = json.load(sys.stdin)
streams = data.get("data_streams", []) or []

paths_to_check = [
    "mysql.tables.size_bytes",
    "mysql.total_size_bytes",
    "backup.xtrabackup.last_backup_size_bytes",
    "backup.xtrabackup_inc.full.last_backup_size_bytes",
    "backup.xtrabackup_inc.inc.last_backup_size_bytes",
    "backup.mysql_dump.last_backup_size_bytes",
]


def curl_json(path, method="GET", body=None):
    cmd = ["curl", "-sS", "-u", f"{es_user}:{es_pass}", "-X", method, f"{es_addr}{path}"]
    if body is not None:
      cmd.extend(["-H", "Content-Type: application/json", "-d", body])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "{}")


def find_type(mapping_root, path):
    current = mapping_root
    for part in path.split("."):
        props = current.get("properties", {})
        if part not in props:
            return None
        current = props[part]
    return current.get("type")


for item in streams:
    name = item.get("name")
    indices = item.get("indices", []) or []
    write_index = indices[-1].get("index_name") if indices else ""
    result = {
        "data_stream": name,
        "write_index": write_index,
        "field_caps": {},
        "mapping_types": {},
        "latest_doc_sample": {},
    }

    field_caps = curl_json(
        f"/{name}/_field_caps?fields=mysql.tables.size_bytes,mysql.total_size_bytes,"
        "backup.xtrabackup.last_backup_size_bytes,"
        "backup.xtrabackup_inc.full.last_backup_size_bytes,"
        "backup.xtrabackup_inc.inc.last_backup_size_bytes,"
        "backup.mysql_dump.last_backup_size_bytes&ignore_unavailable=true"
    )
    for field_name, type_map in (field_caps.get("fields", {}) or {}).items():
        result["field_caps"][field_name] = sorted(type_map.keys())

    if write_index:
        mapping_resp = curl_json(f"/{write_index}/_mapping")
        mapping_root = (((mapping_resp.get(write_index) or {}).get("mappings")) or {})
        for path in paths_to_check:
            result["mapping_types"][path] = find_type(mapping_root, path)

    search_body = json.dumps({
        "size": 1,
        "sort": [{"add_timestamp": {"order": "desc", "unmapped_type": "double"}}],
        "_source": [
            "add_time",
            "collector",
            "mysql.total_size_bytes",
            "mysql.tables.table_name",
            "mysql.tables.size_bytes",
        ],
        "query": {"match_all": {}}
    }, ensure_ascii=False)

    search_resp = curl_json(f"/{name}/_search", "GET", search_body)
    hits = ((search_resp.get("hits") or {}).get("hits") or [])
    if hits:
        source = hits[0].get("_source", {}) or {}
        tables = ((source.get("mysql") or {}).get("tables") or [])
        table_sample = tables[0] if tables else {}
        result["latest_doc_sample"] = {
            "add_time": source.get("add_time"),
            "collector": source.get("collector", {}),
            "mysql.total_size_bytes": (source.get("mysql") or {}).get("total_size_bytes"),
            "mysql.total_size_bytes_python_type": type((source.get("mysql") or {}).get("total_size_bytes")).__name__,
            "mysql.tables[0].table_name": table_sample.get("table_name"),
            "mysql.tables[0].size_bytes": table_sample.get("size_bytes"),
            "mysql.tables[0].size_bytes_python_type": type(table_sample.get("size_bytes")).__name__ if table_sample else None,
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
' "$ES_ADDR" "$ES_USER" "$ES_PASS"

log "检查完成"
if [ -z "$HOST_ID_INDEX" ]; then
  log "如需只检查某一台 Debian 主机，可执行:"
  log "bash check_debian_es_mapping.sh --host-id H_debian_My0b"
fi
