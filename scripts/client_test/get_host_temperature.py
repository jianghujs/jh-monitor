import psutil
import json

def get_temperature_sensors():
    # 检查是否支持传感器
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
        if not temps:
            print(json.dumps({"error": "没有检测到温度传感器。"}, ensure_ascii=False))
            return

        sensors_data = {}
        # 遍历所有可用的传感器信息
        for name, entries in temps.items():
            sensors_data[name] = []
            for entry in entries:
                sensor_info = {
                    "标签": entry.label or "N/A",
                    "当前温度": entry.current,
                    "高温阈值": entry.high,
                    "临界温度": entry.critical
                }
                sensors_data[name].append(sensor_info)

        # 打印 JSON 格式的数据
        print(json.dumps(sensors_data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "当前系统不支持温度传感器读取。"}, ensure_ascii=False))

if __name__ == "__main__":
    get_temperature_sensors()
