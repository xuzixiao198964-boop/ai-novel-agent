import json, time, urllib.request, urllib.error, os
import paramiko

BASE='http://104.244.90.202:9000'
HOST='104.244.90.202'
PW=os.environ.get('DEPLOY_SSH_PASSWORD','v9wSxMxg92dp')

def req(method,path,body=None,timeout=120):
    data=None
    if body is not None:
      data=json.dumps(body,ensure_ascii=False).encode('utf-8')
    r=urllib.request.Request(BASE+path,data=data,method=method,headers={'Content-Type':'application/json','Accept':'application/json'})
    try:
      with urllib.request.urlopen(r,timeout=timeout) as resp:
        t=resp.read().decode('utf-8')
        return resp.status, json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
      t=e.read().decode('utf-8','replace')
      try:j=json.loads(t)
      except: j={'detail':t}
      return e.code,j

# 1) 书架免登录
st,b=req('GET','/api/bookshelf')
assert st==200, ('bookshelf',st,b)

# 2) 连续模式启动不冲掉旧任务
req('POST','/api/tasks/auto-run',{'auto_run':True})
st,t=req('POST','/api/tasks',{'name':'自测-同步清理'})
assert st==200
tid=t['task_id']
st,s=req('POST',f'/api/tasks/{tid}/start',{})
assert st==200 and s.get('ok')
# 立即再次点启动（同 task_id），应返回 queued
st,s2=req('POST',f'/api/tasks/{tid}/start',{})
assert st==200 and s2.get('queued') is True, ('queued',st,s2)
qid=s2.get('queued_task_id')
assert qid

# 3) 等待首任务完成并自动同步到小说平台
for _ in range(180):
    st,c=req('GET','/api/tasks/current')
    if st==200 and not c.get('running'):
      break
    time.sleep(2)
else:
    raise RuntimeError('task not finished in time')

st,m=req('GET',f'/api/tasks/{tid}')
assert st==200
assert m.get('status')=='completed',m
assert m.get('platform_sync_ok') is True,m

st,n=req('GET','/novel-api/novels?page=1&per_page=100')
assert st==200
novels=n.get('novels') or []
assert any(str(x.get('source_task_id') or '')==tid for x in novels), 'not synced to novel platform'

# 4) 超过1天自动清理任务，但书架保留可读（通过 SSH 回写 old updated_at）
ssh=paramiko.SSHClient(); ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()); ssh.connect(HOST,22,'root',PW,timeout=60)
try:
    old='2026-01-01T00:00:00'
    cmd=("python3 - <<'PY'\n"
         "import json\n"
         f"p='/opt/ai-novel-agent/backend/data/tasks/{tid}/meta.json'\n"
         "m=json.load(open(p,'r',encoding='utf-8'))\n"
         "m['status']='completed'\n"
         f"m['updated_at']='{old}'\n"
         "json.dump(m,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)\n"
         "PY")
    _,so,se=ssh.exec_command(cmd,timeout=60)
    so.read(); err=se.read().decode('utf-8','replace')
    if err.strip():
      raise RuntimeError(err)
finally:
    ssh.close()

# 触发清理
req('GET','/api/bookshelf')

st,_=req('GET',f'/api/tasks/{tid}')
assert st==404, ('task not purged',st)

st,toc=req('GET',f'/api/tasks/{tid}/novel/toc')
assert st==200 and (toc.get('chapter_count') or 0)>=1, ('toc fallback failed',st,toc)

print('SELFTEST_OK')
print(json.dumps({'task_id':tid,'queued_task_id':qid,'chapter_count':toc.get('chapter_count')},ensure_ascii=False))
