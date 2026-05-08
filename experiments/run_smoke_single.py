import subprocess, sys, time, os, signal
from pathlib import Path

OUTPUT = '/home/hxm/projects/AgentDNS/experiments/outputs/b2_hard_smoke_runs'
TASKS = '/home/hxm/projects/AgentDNS/experiments/outputs/b2_hard_smoke_12tasks.json'
GROUPS = [
    '直接通用服务组',
    '简单规则路由组',
    '基础解析组',
    '向量召回增强组',
    '信任反馈闭环组',
    '完整多步协同组',
]

Path(OUTPUT).mkdir(parents=True, exist_ok=True)

print("Starting mock service...")
mock = subprocess.Popen(
    ['python3', '/home/hxm/projects/AgentDNS/experiments/mock_services/mock_service.py'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    preexec_fn=os.setsid
)
print(f"Mock started: PID={mock.pid}")

print("Starting backend...")
backend = subprocess.Popen(
    ['python3', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
    cwd='/home/hxm/projects/AgentDNS/agentdns-backend',
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    preexec_fn=os.setsid
)
print(f"Backend started: PID={backend.pid}")

print("Waiting 15s for services to be ready...")
time.sleep(15)

print(f"\nVerifying services are running...")
import requests
try:
    r = requests.get('http://127.0.0.1:8000/docs', timeout=5)
    print(f"Backend OK: {r.status_code}")
except Exception as e:
    print(f"Backend FAILED: {e}")

try:
    r = requests.get('http://127.0.0.1:9002/', timeout=5)
    print(f"Mock OK: {r.status_code}")
except Exception as e:
    print(f"Mock FAILED: {e}")

print("\n" + "="*60)
print("Starting smoke test runs...")
print("="*60 + "\n")

for i, group in enumerate(GROUPS, 1):
    out_dir = Path(OUTPUT) / f'group_{i:02d}_{group}'
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'\n[{i}/{len(GROUPS)}] {group}')

    exp = subprocess.run(
        [sys.executable, '-m', 'experiments.runners.local_http_runner',
         '--group-name', group,
         '--tasks', TASKS,
         '--max-tasks', '12',
         '--output-dir', str(out_dir)],
        cwd='/home/hxm/projects/AgentDNS',
        env={'PYTHONPATH': '/home/hxm/projects/AgentDNS'},
        capture_output=True, text=True, timeout=300
    )
    print(f'  RC={exp.returncode}')
    if exp.stdout:
        lines = exp.stdout.strip().split('\n')
        for l in lines[-5:]:
            print(f'  {l}')

    time.sleep(3)

print("\nTerminating services...")
os.killpg(os.getpgid(backend.pid), signal.SIGTERM)
os.killpg(os.getpgid(mock.pid), signal.SIGTERM)
backend.wait()
mock.wait()
print('B2-hard smoke done')
