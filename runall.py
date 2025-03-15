import subprocess
import sys

def run_scripts():
    # leadership_api.py'yi çalıştırmak için komut
    api_process = subprocess.Popen([sys.executable, "leadership_api2.py"])
    
    # apptts2.py'yi Streamlit ile çalıştırmak için komut
    streamlit_process = subprocess.Popen(["streamlit", "run", "apptts2.py"])
    
    # Her iki sürecin tamamlanmasını beklemek (isteğe bağlı)
    api_process.wait()
    streamlit_process.wait()

if __name__ == "__main__":
    run_scripts()