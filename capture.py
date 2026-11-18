"""Capturas reais do navegador, API e saída dos testes. Não exige servidor prévio."""
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

root = Path(__file__).parent.resolve()
out = root / 'evidencias'
out.mkdir(exist_ok=True)
result = subprocess.run([sys.executable,'-m','unittest','-v','test_app'],cwd=root,text=True,capture_output=True)
log = result.stdout + result.stderr
(out/'testes.txt').write_text(log)
assert result.returncode == 0, log
# Banco exclusivo para as capturas; execução repetível, sem tocar agro.db.
database = out/'captura.db'
if database.exists(): database.unlink()
server_log = (out/'servidor.log').open('w')
server = subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8765'],cwd=root,env={**os.environ,'AGRO_DB':str(database)},stdout=server_log,stderr=server_log)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen('http://127.0.0.1:8765/health'); break
        except OSError: time.sleep(.1)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1280,'height':880},device_scale_factor=1)
        base = 'http://127.0.0.1:8765'
        def snap(name): page.screenshot(path=str(out/name),full_page=True)
        page.goto(base)
        snap('01-login.png')
        page.locator('#username').fill('produtor_demo')
        page.locator('#password').fill('Demonstracao!2026')
        page.get_by_role('button',name='Criar conta').click()
        page.wait_for_function("document.querySelector('#notice').textContent.includes('Conta criada')")
        snap('02-cadastro.png')
        page.get_by_role('button',name='Entrar',exact=True).click()
        page.locator('#workspace').wait_for(state='visible')
        for name,crop,area in [('Talhão Norte','Milho','12.5'),('Talhão Sul','Soja','8.75')]:
            page.locator('#name').fill(name); page.locator('#crop').fill(crop); page.locator('#area').fill(area)
            page.get_by_role('button',name='Salvar talhão').click()
            page.wait_for_function('document.querySelector("#name").value === ""')
        assert page.locator('#rows tr').count()==2
        snap('03-listagem.png')
        page.get_by_role('button',name='Editar',exact=True).first.click()
        page.locator('#crop').fill('Milho safrinha')
        snap('04-edicao.png')
        page.get_by_role('button',name='Salvar talhão').click()
        page.wait_for_function("document.querySelector('#rows').textContent.includes('Milho safrinha')")
        page.on('dialog',lambda dialog:dialog.accept())
        page.get_by_role('button',name='Excluir',exact=True).last.click()
        page.wait_for_function("document.querySelectorAll('#rows tr').length===1")
        snap('05-exclusao.png')
        page.get_by_role('button',name='Sair com segurança').click()
        page.wait_for_function("document.querySelector('#notice').textContent.includes('revogado')")
        snap('06-logout.png')
        api = page.request
        credentials={'username':'produtor_demo','password':'Demonstracao!2026'}
        token=api.post(base+'/auth/login',data=credentials).json()['access_token']
        auth={'Authorization':'Bearer '+token}
        api.post(base+'/auth/register',data={'username':'vizinho_demo','password':'Demonstracao!2026'})
        other=api.post(base+'/auth/login',data={'username':'vizinho_demo','password':'Demonstracao!2026'}).json()['access_token']
        probes=[]
        def probe(label,response,expected):
            assert response.status==expected,(label,response.status)
            probes.append({'requisicao':label,'status':response.status,'resposta':response.json() if response.status!=204 else None})
        probe('GET /fields sem token',api.get(base+'/fields'),401)
        probe('GET /fields/1 com usuário vizinho',api.get(base+'/fields/1',headers={'Authorization':'Bearer '+other}),404)
        probe('POST /fields com área negativa',api.post(base+'/fields',headers=auth,data={'name':'Inválido','crop':'Milho','area_ha':-1}),422)
        probe('POST /auth/logout',api.post(base+'/auth/logout',headers=auth),204)
        probe('GET /fields com token revogado',api.get(base+'/fields',headers=auth),401)
        (out/'seguranca.json').write_text(json.dumps(probes,ensure_ascii=False,indent=2))
        def evidence_page(title,text,filename):
            document='<html lang="pt-BR"><meta charset="utf-8"><style>body{background:#f2f6ed;color:#163a2b;padding:35px;font:18px system-ui}pre{background:white;padding:25px;border-left:5px solid #286b49;white-space:pre-wrap;font:17px monospace}</style><h1>'+title+'</h1><p>Saída real da execução local · evidência técnica</p><pre>'+html.escape(text)+'</pre></html>'
            path=out/(filename+'.html');path.write_text(document)
            page.goto(path.as_uri());snap(filename+'.png')
        evidence_page('Segurança · respostas HTTP',json.dumps(probes,ensure_ascii=False,indent=2),'07-seguranca')
        evidence_page('Testes automatizados · unittest',log,'08-testes')
        schema=api.get(base+'/openapi.json').json()
        (root/'openapi.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2))
        page.goto(base+'/docs');page.locator('.swagger-ui .opblock').first.wait_for(timeout=60000)
        snap('09-swagger.png')
        page.get_by_text('/fields',exact=True).first.click()
        snap('10-swagger-detalhe.png')
        browser.close()
    print(log)
    print('Fluxo navegador: cadastro, login, criação, edição, exclusão e logout OK; 5 verificações HTTP OK; 10 PNGs reais.')
finally:
    server.terminate();server.wait(timeout=10);server_log.close()
