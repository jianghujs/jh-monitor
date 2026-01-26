import ansible_runner
import json
import tempfile

def _normalize_script_items(script_names):
    items = []
    for item in script_names:
        if isinstance(item, dict):
            name = item.get('name') or item.get('script') or item.get('script_name') or item.get('file')
            args = item.get('args', '')
        else:
            name = str(item)
            args = ''
        if not name:
            continue
        items.append({'name': name, 'args': args})
    return items

def _normalize_target_hosts(target_hosts):
    if not target_hosts:
        return None
    if isinstance(target_hosts, (list, tuple, set)):
        host_list = [str(host) for host in target_hosts if host]
        return ','.join(host_list) if host_list else None
    return str(target_hosts)

def run_script_batch(script_names, target_hosts=None):
    normalized_scripts = _normalize_script_items(script_names)
    print("Running scripts:", normalized_scripts)
    jh_monitor_path = '/www/server/jh-monitor/'
    playbook_path = f'{jh_monitor_path}scripts/client/run_script_batch.yml'  # 替换为你的 Playbook 文件路径
    
    # 使用 ansible-runner 执行 Playbook
    
    with tempfile.TemporaryDirectory() as tmpdir:
        extravars = {'script_names': normalized_scripts}
        target_hosts = _normalize_target_hosts(target_hosts)
        if target_hosts:
            extravars['target_hosts'] = target_hosts
        r = ansible_runner.run(
            private_data_dir=tmpdir, 
            playbook=playbook_path,
            extravars=extravars  # 传递参数列表
        )

        if r.status == 'successful':
            print("Playbook executed successfully")
        else:
            print("Playbook execution failed")

        result = {}
        for event in r.events:
            if event.get('event') == 'runner_on_ok':
                event_data = event.get('event_data', {})
                task_name = event_data.get('task', '')
                
                if task_name == 'Return Results':
                    
                    # IP地址
                    ip = event_data.get('host', '')
                    # 返回结果
                    res = event_data.get('res', {})
                    r = {item.get('msg', '')[0]: item.get('msg', '')[1] for item in res.get('results', [])}
                    
                    result[ip] = {
                        'status': 'ok',
                        'data': r
                    }
            elif event.get('event') == 'runner_on_unreachable': 
                event_data = event.get('event_data', {})
                ip = event_data.get('host', '')
                result[ip] = {
                    'status': 'fail',
                    'msg': 'unreachable'
                }

        return result

# if __name__ == "__main__":
#     script_outputs = run_script_batch(['get_host_info.py', 'get_host_usage.py'])
#     # script_outputs = run_script_batch(['get_host_usage.py'])

#     print("✨", script_outputs)
