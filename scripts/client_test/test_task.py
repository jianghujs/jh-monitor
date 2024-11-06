import ansible_runner
import json

def run_ansible_playbook():
    playbook_path = './get_host_info.yml'  # 替换为你的 Playbook 文件路径

    # 使用 ansible-runner 执行 Playbook
    r = ansible_runner.run(private_data_dir='.', playbook=playbook_path)

    if r.status == 'successful':
        print("Playbook executed successfully")
    else:
        print("Playbook execution failed")
    print("r", r)
    # 把r转为json字符串
    print("Final status: ", r.status)
    print("Final rc: ", r.rc)

    
    # 查找并打印 Python 脚本的执行结果
    for event in r.events:
        # 查找包含任务结果的事件
        if 'event_data' in event and 'task' in event['event_data']:
            if event['event_data']['task'] == 'Return Result': 
                print("evernt", event)
                if 'res' in event['event_data'] and 'result.stdout' in event['event_data']['res']:
                    host = event['event_data']['host']
                    script_output = event['event_data']['res']['result.stdout']
                    print("✅ ===================== Python script output:")
                    print(script_output)

if __name__ == "__main__":
    run_ansible_playbook()
