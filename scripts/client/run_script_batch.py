import ansible_runner
import json

def run_script_batch(script_names):
    print("Running scripts:", script_names)
    jh_monitor_path = '/www/server/jh-monitor/'
    playbook_path = f'{jh_monitor_path}scripts/client/run_script_batch.yml'  # 替换为你的 Playbook 文件路径
    
    # 使用 ansible-runner 执行 Playbook
    r = ansible_runner.run(
        private_data_dir=f'{jh_monitor_path}/data', 
        playbook=playbook_path,
        extravars={'script_names': script_names}  # 传递参数列表
    )

    if r.status == 'successful':
        print("Playbook executed successfully")
    else:
        print("Playbook execution failed")

    result = []
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
                
                result.append({
                    'ip': ip,
                    'data': r
                })
                
    return result

# if __name__ == "__main__":
#     script_outputs = run_script_batch(['get_host_info.py', 'get_host_usage.py'])
#     # script_outputs = run_script_batch(['get_host_usage.py'])
