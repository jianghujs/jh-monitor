#!/bin/bash

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

NET_ENV_CN="${1}"
PKG_MANAGER=""
APT_UPDATED=0

log() {
  echo "[python-env] $*"
}

err() {
  echo "[python-env] ERROR: $*" >&2
}

check_command_exist() {
  command -v "$@" >/dev/null 2>&1
}

detect_pkg_manager() {
  if check_command_exist apt-get; then
    echo "apt"
    return
  fi
  if check_command_exist dnf; then
    echo "dnf"
    return
  fi
  if check_command_exist yum; then
    echo "yum"
    return
  fi
  if check_command_exist zypper; then
    echo "zypper"
    return
  fi
  echo ""
}

install_packages() {
  if [ -z "$PKG_MANAGER" ]; then
    err "No supported package manager found."
    return 1
  fi

  case "$PKG_MANAGER" in
    apt)
      if [ "$APT_UPDATED" -eq 0 ]; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y
        APT_UPDATED=1
      fi
      apt-get install -y --no-install-recommends "$@"
      ;;
    dnf)
      dnf -y install "$@"
      ;;
    yum)
      yum -y install "$@"
      ;;
    zypper)
      zypper -n install "$@"
      ;;
    *)
      err "Unsupported package manager: $PKG_MANAGER"
      return 1
      ;;
  esac
}

ensure_python3() {
  if check_command_exist python3; then
    return 0
  fi

  log "python3 not found, installing..."
  install_packages python3 || true

  if ! check_command_exist python3 && check_command_exist python36; then
    ln -sf "$(command -v python36)" /usr/bin/python3
  fi

  if ! check_command_exist python3 && check_command_exist python; then
    if python - <<'PY' >/dev/null 2>&1
import sys
sys.exit(0 if sys.version_info[0] == 3 else 1)
PY
    then
      ln -sf "$(command -v python)" /usr/bin/python3
    fi
  fi

  if ! check_command_exist python3; then
    err "python3 is still missing after install."
    return 1
  fi
}

ensure_pip() {
  if python3 -m pip --version >/dev/null 2>&1; then
    return 0
  fi

  log "pip not found, installing..."
  install_packages python3-pip || true

  if python3 -m pip --version >/dev/null 2>&1; then
    return 0
  fi

  python3 -m ensurepip --upgrade >/dev/null 2>&1 || true

  if python3 -m pip --version >/dev/null 2>&1; then
    return 0
  fi

  err "pip is still missing after install."
  return 1
}

python_module_installed() {
  local module="$1"
  python3 - <<PY >/dev/null 2>&1
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("$module") else 1)
PY
}

ensure_python_module() {
  local module="$1"
  local pkg_name="$2"

  if python_module_installed "$module"; then
    return 0
  fi

  if [ -n "$pkg_name" ]; then
    log "Installing $module via system package: $pkg_name"
    install_packages "$pkg_name" || true
  fi

  if python_module_installed "$module"; then
    return 0
  fi

  ensure_pip || return 1

  if [ "$NET_ENV_CN" = "cn" ]; then
    export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
    export PIP_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn"
  fi

  log "Installing $module via pip"
  python3 -m pip install "$module"

  if ! python_module_installed "$module"; then
    err "Failed to install Python module: $module"
    return 1
  fi
}

main() {
  PKG_MANAGER="$(detect_pkg_manager)"
  ensure_python3 || return 1

  local psutil_pkg=""
  local flask_pkg=""

  case "$PKG_MANAGER" in
    apt|dnf|yum)
      psutil_pkg="python3-psutil"
      flask_pkg="python3-flask"
      ;;
    zypper)
      psutil_pkg="python3-psutil"
      flask_pkg="python3-Flask"
      ;;
    *)
      psutil_pkg=""
      flask_pkg=""
      ;;
  esac

  ensure_python_module "psutil" "$psutil_pkg" || return 1
  ensure_python_module "flask" "$flask_pkg" || return 1

  log "Python environment is ready."
}

main "$@"
