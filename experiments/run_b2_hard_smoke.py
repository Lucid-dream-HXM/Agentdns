import subprocess, sys, time, json
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
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
time.sleep(3)

print("Starting backend...")
backend = subprocess.Popen(
    ['python3', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
time.sleep(15)

print(f"Backend PID: {backend.pid}")
time.sleep(2)

for i, group in enumerate(GROUPS, 1):
    print(f'\n===== [{i}/{len(GROUPS)}] 运行 {group} =====')

    out_dir = Path(OUTPUT) / f'group_{i:02d}_{group}'
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
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
        print('RC=', exp.returncode)
        if exp.stdout:
            lines = exp.stdout.strip().split('\n')
            print('\n'.join(lines[-10:]))
        if exp.stderr:
            lines = exp.stderr.strip().split('\n')
            print('\n'.join(lines[-5:]))
    except subprocess.TimeoutExpired:
        print(f'TIMEOUT: group {group} exceeded 300s')
    except Exception as e:
        print(f'ERROR: {e}')

    time.sleep(2)

print("\nTerminating services...")
backend.terminate()
backend.wait()
mock.terminate()
mock.wait()
print('B2-hard smoke done')
