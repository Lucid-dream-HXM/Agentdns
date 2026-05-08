
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path
ROOT = Path("/home/hxm/projects/AgentDNS")
OUTPUT = ROOT / "experiments" / "outputs" / "b3_drift_formal_120runs"
TASKS = ROOT / "experiments" / "outputs" / "b3_drift_120tasks.json"
GROUPS = ["直接通用服务组","简单规则路由组","基础解析组","向量召回增强组","信任反馈闭环组","完整多步协同组"]

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mock = subprocess.Popen(["python3", str(ROOT/"experiments/mock_services/mock_service.py")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(3)
    backend = subprocess.Popen(["python3","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(ROOT/"agentdns-backend"))
    time.sleep(10)
    for i, group in enumerate(GROUPS, 1):
        print(f"\n===== [{i}/{len(GROUPS)}] 运行 {group} =====")
        exp = subprocess.run([sys.executable,"-m","experiments.runners.local_http_runner","--group-name",group,"--tasks",str(TASKS),"--max-tasks","120","--output-dir",str(OUTPUT)], cwd=str(ROOT), env={"PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=7200)
        print("RC=", exp.returncode)
        if exp.stdout: print(exp.stdout.strip()[-3000:])
        if exp.stderr: print(exp.stderr.strip()[-1200:])
    backend.terminate(); backend.wait()
    mock.terminate(); mock.wait()
    print("b3 drift formal 120 done")
if __name__ == "__main__":
    main()
