
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
ROOT = Path("/home/hxm/projects/AgentDNS")
OUTPUT = ROOT / "experiments" / "outputs" / "b3_drift_smoke_runs"
TASKS_120 = ROOT / "experiments" / "outputs" / "b3_drift_120tasks.json"
TASKS_SMOKE = ROOT / "experiments" / "outputs" / "b3_drift_smoke_12tasks.json"
GROUPS = ["直接通用服务组","简单规则路由组","基础解析组","向量召回增强组","信任反馈闭环组","完整多步协同组"]

def build_smoke_tasks():
    data = json.loads(TASKS_120.read_text(encoding="utf-8"))
    tasks = data["tasks"]
    t1 = [t for t in tasks if t["required_service_categories"] == ["translation"]][:4]
    t2 = [t for t in tasks if t["required_service_categories"] == ["text_summary"]][:4]
    t3 = [t for t in tasks if t["required_service_categories"] == ["structured_extraction"]][:4]
    mixed = []
    for i in range(4):
        mixed += [t1[i], t2[i], t3[i]]
    TASKS_SMOKE.write_text(json.dumps({"tasks": mixed}, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    build_smoke_tasks()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mock = subprocess.Popen(["python3", str(ROOT/"experiments/mock_services/mock_service.py")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(3)
    backend = subprocess.Popen(["python3","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(ROOT/"agentdns-backend"))
    time.sleep(10)
    for i, group in enumerate(GROUPS, 1):
        print(f"\n===== [{i}/{len(GROUPS)}] 运行 {group} =====")
        exp = subprocess.run([sys.executable,"-m","experiments.runners.local_http_runner","--group-name",group,"--tasks",str(TASKS_SMOKE),"--max-tasks","12","--output-dir",str(OUTPUT)], cwd=str(ROOT), env={"PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=1800)
        print("RC=", exp.returncode)
        if exp.stdout: print(exp.stdout.strip()[-2000:])
        if exp.stderr: print(exp.stderr.strip()[-1000:])
    backend.terminate(); backend.wait()
    mock.terminate(); mock.wait()
    print("b3 drift smoke done")
if __name__ == "__main__":
    main()
