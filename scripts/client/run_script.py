import ansible_runner
import json

def run_script(script_name):
    print("run_script", script_name)
    
    playbook_path = '/www/server/jh-monitor/scripts/client/run_script.yml'  # 替换为你的 Playbook 文件路径
    
    # 使用 ansible-runner 执行 Playbook
    r = ansible_runner.run(
        private_data_dir='.', 
        playbook=playbook_path,
        extravars={'script_name': script_name}  # 传递参数
    )

    if r.status == 'successful':
        print("Playbook executed successfully")
    else:
        print("Playbook execution failed")

    result = {}
    for event in r.events:
        # 查找包含任务结果的事件
        if 'event_data' in event and 'task' in event['event_data']:
            if event['event_data']['task'] == 'Return Result': 
                print("evernt", event)
                if 'res' in event['event_data'] and 'result.stdout' in event['event_data']['res']:
                    host = event['event_data']['host']
                    script_output = event['event_data']['res']['result.stdout']
                    result[host] = script_output
    
    return result

        
if __name__ == "__main__":
    run_script('get_host_info.py')
