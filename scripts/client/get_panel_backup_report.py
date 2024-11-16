# backup_report.py
import json
import sys
import os

def get_panel_backup_report():
    try:
        jhpanel_path = '/www/server/jh-panel'
        # 如果系统不存在目录，直接返回{}
        if not os.path.exists(jhpanel_path):
            return {}
        
        sys.path.append('/www/server/jh-panel/scripts')
        from report import reportTools
        # 实例化 reportTools 类
        report_tool = reportTools()
        
        # 调用 getBackupReport 方法
        report = report_tool.getBackupReport()
        
        return report
    except Exception as e:
        print(f"An error occurred while getting the backup report: {e}")
        return {}

def main():
    panel_backup_report = get_panel_backup_report()
    print(json.dumps(panel_backup_report, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    main()
