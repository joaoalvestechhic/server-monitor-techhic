import os
import psutil
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

class ServerMonitor:
    def __init__(self):
        self._config = {
            "interval": 300,
            "alert_cpu_threshold": 90,
            "alert_memory_threshold": 85,
            "api_endpoint": "https://monitor.hikdev.internal/metrics",
            "auth_key": os.getenv('AUTH_KEY')
        }
        self.last_alert = None
        self.alert_cooldown = 3600

    def get_system_metrics(self):
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_connections": len(psutil.net_connections())
            }
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    if pinfo['cpu_percent'] > 5:
                        processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            metrics["top_processes"] = sorted(
                processes,
                key=lambda x: x['cpu_percent'],
                reverse=True
            )[:5]
            
            return metrics
            
        except Exception as e:
            print(f"Erro ao coletar métricas: {e}")
            return None

    def should_alert(self, metrics):
        if not metrics:
            return False
            
        if self.last_alert and time.time() - self.last_alert < self.alert_cooldown:
            return False
            
        return (
            metrics["cpu_percent"] > self._config["alert_cpu_threshold"] or
            metrics["memory_percent"] > self._config["alert_memory_threshold"]
        )

    def send_metrics(self, metrics):
        try:
            headers = {
                "Authorization": f"Bearer {self._config['auth_key']}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self._config["api_endpoint"],
                headers=headers,
                data=json.dumps(metrics)
            )
            
            if response.status_code != 200:
                print(f"Erro ao enviar métricas: {response.status_code}")
                
        except Exception as e:
            print(f"Erro na comunicação com API: {e}")

    def run(self):
        print("Iniciando monitoramento do servidor...")
        
        while True:
            metrics = self.get_system_metrics()
            
            if metrics:
                print(f"\nMétricas coletadas em {metrics['timestamp']}:")
                print(f"CPU: {metrics['cpu_percent']}%")
                print(f"Memória: {metrics['memory_percent']}%")
                print(f"Disco: {metrics['disk_usage']}%")
                
                if self.should_alert(metrics):
                    print("\n⚠️ ALERTA: Uso elevado de recursos!")
                    self.last_alert = time.time()
                
                self.send_metrics(metrics)
            
            time.sleep(self._config["interval"])

if __name__ == "__main__":
    monitor = ServerMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nMonitoramento finalizado pelo usuário.")
