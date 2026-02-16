import os
import json
import time
from datetime import datetime

class StopwatchMonitor:
    def __init__(self, directory="."):
        self.directory = directory
        self.signal_file = os.path.join(directory, "start_signal.json")
        self.start_time = None
        self.running = False
    
    def check_signal(self):
        """Check if start_signal.json exists and start/stop stopwatch accordingly"""
        if os.path.exists(self.signal_file):
            if not self.running:
                # Start the stopwatch
                self.start_time = time.time()
                self.running = True
                print(f"⏱️  Kronometre başladı: {datetime.now().strftime('%H:%M:%S')}")
                
                # Update the signal file with start timestamp
                with open(self.signal_file, 'w') as f:
                    json.dump({
                        "status": "running", 
                        "start_time": datetime.now().isoformat()
                    }, f)
        else:
            if self.running:
                # Stop the stopwatch
                elapsed = time.time() - self.start_time
                self.running = False
                print(f"⏹️  Kronometre durdu: {datetime.now().strftime('%H:%M:%S')}")
                print(f"⏱️  Geçen süre: {elapsed:.2f} saniye")
                return elapsed
        return None
    
    def start_monitoring(self):
        """Start monitoring the directory for signal file"""
        print("📁 Klasör izlenmeye başlandı...")
        print("📝 start_signal.json oluşturulduğunda kronometre başlar")
        print("🗑️  start_signal.json silindiğinde kronometre durur")
        print("-" * 50)
        
        try:
            while True:
                elapsed = self.check_signal()
                if elapsed is not None:
                    print("✅ İşlem tamamlandı!")
                    break
                time.sleep(0.5)  # Check every 500ms
        except KeyboardInterrupt:
            print("\n⏹️  İzleme durduruldu")
            if self.running:
                elapsed = time.time() - self.start_time
                print(f"⏱️  Son geçen süre: {elapsed:.2f} saniye")

if __name__ == "__main__":
    monitor = StopwatchMonitor()
    monitor.start_monitoring()
