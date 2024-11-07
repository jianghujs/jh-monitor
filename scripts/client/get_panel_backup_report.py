# backup_report.py
import sys
sys.path.append('/www/server/jh-panel/scripts')

from report import reportTools

def main():
    try:
        # 实例化 reportTools 类
        report_tool = reportTools()
        
        # 调用 getBackupReport 方法
        report = report_tool.getBackupReport()
        
        # 打印备份报告
        print("Backup Report:")
        print(report)
    except Exception as e:
        print(f"An error occurred while getting the backup report: {e}")

if __name__ == "__main__":
    main()
