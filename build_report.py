"""Gera PDF a partir de capturas e resultados reais já existentes."""
from pathlib import Path
from xml.sax.saxutils import escape
import json
import zipfile
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Preformatted
import pymupdf as fitz

root = Path(__file__).parent.resolve()
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyPT',fontName='Helvetica',fontSize=12,leading=18,spaceAfter=12,textColor=colors.HexColor('#193b2d')))
styles['Title'].textColor=colors.HexColor('#193b2d')
styles['Heading1'].textColor=colors.HexColor('#246846')
W,H=landscape(A4)
story=[]
def title(t): story.append(Paragraph(t,styles['Heading1']))
def para(t): story.append(Paragraph(t,styles['BodyPT']))
def new(): story.append(PageBreak())
def image_page(title_text,caption,filename):
    new(); title(title_text);para(caption)
    path=root/'evidencias'/filename
    im=PILImage.open(path)
    if filename == '08-testes.png':
        path=root/'evidencias'/'08-testes-recorte.png'
        im=im.crop((0,0,1280,520));im.save(path)
    w,h=im.size
    scale=min((W-84)/w,(H-185)/h)
    story.append(Image(str(path),width=w*scale,height=h*scale))

title('AgroTalhões | Atividade Prática 3')
para('<b>IAL-221 — Arquitetura de APIs</b><br/>Professor: Joel Coutinho de Souza')
para('<b>Integrante único:</b> Otávio Pires de Campos Arruda Falcão<br/><b>Curso:</b> Big Data no Agronegócio — 6º termo<br/><b>Instituição:</b> FATEC Shunji Nishimura — Pompeia/SP')
para('Aplicação REST em Python para cadastro, consulta, atualização e exclusão de talhões agrícolas, com autenticação, autorização por proprietário e persistência em SQLite.')
para('<b>Entrega preparada:</b> relatório, código-fonte, testes, contrato OpenAPI e evidências reais.<br/><b>Prazo do enunciado:</b> 18/11/2026. Canal indicado: joel.souza@cps.sp.gov.br.<br/>Relatório acompanhado do código e das evidências de execução.')
para('<b>Repositório GitHub:</b><br/><link href="https://github.com/FalcaoOtavio/atividade-pratica-3-arquitetura-apis">https://github.com/FalcaoOtavio/atividade-pratica-3-arquitetura-apis</link><br/>O código completo também acompanha o ZIP.')
new();title('1. Objetivo, arquitetura e contrato REST')
para('O sistema organiza o nome, a cultura e a área de cada talhão. Um produtor cria sua conta e gerencia somente os seus dados. O tema foi escolhido pela relação com o curso de Big Data no Agronegócio, sem depender de serviços externos ou dados pessoais reais.')
para('<b>Fluxo:</b> navegador HTML/JavaScript → requisições HTTP/JSON → rotas FastAPI → validação Pydantic e autenticação → SQL parametrizado → SQLite. O banco contém usuários, sessões e talhões; cada talhão referencia seu proprietário.')
para('<b>Recursos:</b> POST /auth/register e /auth/login; GET /auth/me; POST /auth/logout; GET e POST /fields; GET, PUT e DELETE /fields/{field_id}. PUT substitui os campos editáveis do recurso. O ID e o proprietário são definidos pelo servidor.')
para('<b>Semântica HTTP:</b> 200 para consulta e atualização; 201 e Location para criação; 204 para exclusão/logout; 401 sem sessão válida; 404 para recurso ausente ou de terceiro; 409 para usuário duplicado; 422 para entrada inválida. O contrato OpenAPI descreve modelos, respostas de sucesso, validação e segurança Bearer.')
para('FastAPI publica Swagger em /docs e o contrato em /openapi.json. A interface consome as mesmas rotas documentadas; não acessa diretamente o banco. Não há SOAP, pois o enunciado permite REST ou SOAP.')
new();title('2. Controles de segurança e limites')
para('<b>Autenticação:</b> senha entre 12 e 128 caracteres, PBKDF2-HMAC-SHA256 com 600.000 iterações e salt aleatório de 16 bytes. A senha não é armazenada em texto. A comparação do hash usa hmac.compare_digest.')
para('<b>Sessão:</b> token opaco aleatório de 32 bytes, transmitido no cabeçalho Authorization: Bearer. Apenas seu hash SHA-256 fica no banco; a validade é de uma hora. Logout apaga a sessão. A UI mantém o token apenas em memória, sem localStorage.')
para('<b>Autorização:</b> leitura e escrita filtram ID e proprietário autenticado. Recurso alheio retorna 404, evitando revelar sua existência. Queries parametrizadas reduzem risco de injeção SQL. A UI usa textContent para dados cadastrados, evitando interpretar HTML como código.')
para('<b>Validação:</b> nome e cultura têm limites de tamanho; área deve ser finita, positiva e até 100.000 hectares. Campos extras são rejeitados, inclusive tentativas de enviar owner. Respostas incluem nosniff, DENY, no-referrer e no-store.')
para('<b>Limites:</b> demonstração local em HTTP, sem rate limiting, recuperação de senha, paginação ou backup automático. Antes de publicar como serviço, adicionar HTTPS, limitação de tentativas e operação segura. Não se afirma que o protótipo esteja pronto para produção.')
for t,c,f in [
('3. Acesso à aplicação','Figura 1 — Tela inicial real, com acesso ao Swagger, OpenAPI e formulário de autenticação.','01-login.png'),
('4. Cadastro de usuário','Figura 2 — Conta criada pela interface; confirmação recebida após POST /auth/register.','02-cadastro.png'),
('5. Listagem e criação','Figura 3 — Dois talhões persistidos, com culturas e total de hectares; formulário de novo registro.','03-listagem.png'),
('6. Edição de talhão','Figura 4 — Edição carregada a partir da listagem. O teste de navegador salvou e verificou Milho safrinha.','04-edicao.png'),
('7. Exclusão confirmada','Figura 5 — Exclusão executada após confirmação; permanece somente o Talhão Norte.','05-exclusao.png'),
('8. Encerramento da sessão','Figura 6 — Logout real. A API revoga o token e a interface volta ao formulário de acesso.','06-logout.png'),
]: image_page(t,c,f)
# Cortes da captura original preservam os pixels e melhoram a legibilidade no PDF.
for filename,cut in [('07-seguranca.png',600),('09-swagger.png',802),('10-swagger-detalhe.png',1080)]:
    original=PILImage.open(root/'evidencias'/filename)
    for i,(top,bottom) in enumerate([(0,cut),(cut,original.height)],1):
        original.crop((0,top,original.width,bottom)).save(root/'evidencias'/f'{Path(filename).stem}-parte{i}.png')
image_page('9. Evidências de segurança — parte 1','Figura 7a — Respostas HTTP reais: acesso sem token (401), recurso de terceiro (404) e entrada inválida (422). Página local exibe o JSON capturado, sem simulação.','07-seguranca-parte1.png')
image_page('10. Evidências de segurança — parte 2','Figura 7b — Continuação do JSON real: logout (204) e recusa do token revogado (401).','07-seguranca-parte2.png')
image_page('11. Testes de integração e contrato','Figura 8 — Captura de página local com a saída real de python -m unittest -v test_app. Quatro métodos passaram; detalhes completos em evidencias/testes.txt.','08-testes.png')
image_page('12. Documentação Swagger — visão geral','Figura 9a — Swagger carregado da aplicação em execução: versão, autorização Bearer e rotas de autenticação.','09-swagger-parte1.png')
image_page('13. Documentação Swagger — recursos e modelos','Figura 9b — Continuação da tela: métodos dos talhões e modelos de entrada e saída.','09-swagger-parte2.png')
image_page('14. Documentação Swagger — operação expandida','Figura 10a — GET /fields expandido na interface Swagger real. O contrato também acompanha o código em openapi.json.','10-swagger-detalhe-parte1.png')
image_page('15. Documentação Swagger — resposta e schemas','Figura 10b — Continuação da operação expandida e modelos gerados.','10-swagger-detalhe-parte2.png')
new();title('16. Verificação, reprodução e conclusão')
para('<b>Testes executados:</b> test_auth (cadastro, login, credencial errada, duplicidade, senha curta e revogação); test_crud_isolation_validation (CRUD, isolamento entre dois usuários, área inválida e campo extra); test_health; test_ui_contract_and_security (HTML, OpenAPI, Bearer, Swagger, hash/salt, expiração e cabeçalho de segurança).')
para('<b>Navegador real:</b> Chromium via Playwright verificou cadastro, login, criação de dois talhões, edição, exclusão e logout. Cinco sondagens adicionais confirmaram os códigos HTTP de segurança. Não foram realizados testes de carga, pentest ou medição de cobertura percentual.')
para('<b>Reprodução:</b> criar ambiente virtual; instalar requirements.txt; executar python -m uvicorn app:app --host 127.0.0.1 --port 8000; abrir http://127.0.0.1:8000. Testar com python -m unittest -v test_app. Para reconstruir evidências e relatório, instalar requirements-evidencias.txt e Chromium, executar capture.py e build_report.py.')
para('<b>Conclusão:</b> o protótipo demonstra recursos REST com persistência, documentação e controles de acesso verificáveis. Todos os fluxos locais descritos foram exercitados. O repositório indicado reúne código, testes e evidências para reprodução.')
para('<b>Fontes e referência técnica:</b> enunciado “Atividade Prática 3 — IAL-221 — Arquitetura de APIs”, professor Joel Coutinho de Souza; documentação oficial FastAPI: https://fastapi.tiangolo.com/; OpenAPI: https://spec.openapis.org/oas/latest.html; Python hashlib: https://docs.python.org/3/library/hashlib.html. As evidências de execução são os arquivos locais anexos.')
def footer(canvas,doc):
    canvas.setFont('Helvetica',9);canvas.setFillColor(colors.HexColor('#526452'))
    canvas.drawString(36,22,'AgroTalhões | Otávio Pires de Campos Arruda Falcão | IAL-221')
    canvas.drawRightString(W-36,22,str(doc.page))
SimpleDocTemplate(str(root/'relatorio.pdf'),pagesize=(W,H),rightMargin=36,leftMargin=36,topMargin=30,bottomMargin=38,title='AgroTalhões — Atividade Prática 3',author='Otávio Pires de Campos Arruda Falcão').build(story,onFirstPage=footer,onLaterPages=footer)
doc=fitz.open(root/'relatorio.pdf')
validation={'pages':len(doc),'text_chars':[len(p.get_text()) for p in doc],'images_per_page':[len(p.get_images()) for p in doc]}
assert all(validation['text_chars'])
assert 'Otávio Pires de Campos Arruda Falcão' in doc[0].get_text()
render=root/'verificacao_pdf';render.mkdir(exist_ok=True)
for i,page in enumerate(doc): page.get_pixmap(matrix=fitz.Matrix(1,1)).save(render/f'pagina-{i+1:02d}.png')
(root/'verificacao_pdf.json').write_text(json.dumps(validation,indent=2))
with zipfile.ZipFile(root/'atividade-pratica-3.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if p.is_file() and not any(part in {'.venv','__pycache__','verificacao_pdf','.git'} for part in rel.parts) and p.suffix not in {'.db','.zip','.log'}:
            z.write(p,rel)
with zipfile.ZipFile(root/'atividade-pratica-3.zip') as z:
    assert z.testzip() is None
    assert {'app.py','test_app.py','README.md','relatorio.pdf','openapi.json'} <= set(z.namelist())
print(json.dumps(validation));print('PDF renderizado; ZIP íntegro e com código, relatório e evidências.')
