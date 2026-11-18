# AgroTalhões — Atividade Prática 3

Aplicação REST acadêmica para gestão de talhões agrícolas. Python, FastAPI, SQLite e interface HTML/JavaScript. Autor: Otávio Pires de Campos Arruda Falcão. IAL-221 — Arquitetura de APIs, FATEC Shunji Nishimura, Big Data no Agronegócio, 6º termo.

## Executar

Python 3.11 ou superior (execução verificada com Python 3.14).

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000. Crie uma conta (usuário: letras, números, _ e -; senha: 12 a 128 caracteres), entre e cadastre um talhão. Não existem contas nem senhas fixas na aplicação. Os dados persistem em `agro.db`; `AGRO_DB` permite outro caminho. Para reiniciar os dados, pare o servidor e remova exclusivamente o banco de demonstração.

- Swagger: http://127.0.0.1:8000/docs
- Contrato: http://127.0.0.1:8000/openapi.json
- Saúde: http://127.0.0.1:8000/health

## Testar

```sh
python -m unittest -v test_app
```

Quatro métodos de teste integram aplicação e SQLite temporário: autenticação/revogação, CRUD/isolamento/validação, saúde, interface/contrato/expiração/hash. Não alteram o banco de uso normal. Asserções verificam 201, 200, 204, 401, 404, 409 e 422. `evidencias/testes.txt` contém a saída real.

## Reproduzir capturas e relatório

```sh
python -m pip install -r requirements-evidencias.txt
python -m playwright install chromium
python capture.py
python build_report.py
```

O script inicia um servidor temporário na porta local 8765, executa o fluxo de navegador, gera PNGs reais, salva respostas HTTP, exporta OpenAPI e para o servidor. Usa apenas `evidencias/captura.db`, recriado a cada execução. `07-seguranca.png` e `08-testes.png` são capturas de páginas locais que exibem, sem alterar, as respostas reais e a saída real de unittest. Não são terminais simulados. Swagger usa seus recursos CDN padrão; conexão à Internet é necessária para carregar sua interface.

## API

| Método | Recurso | Resultado |
|---|---|---|
| POST | /auth/register | Cadastro, 201 |
| POST | /auth/login | Token opaco de uma hora, 200 |
| GET | /auth/me | Usuário autenticado |
| POST | /auth/logout | Revoga token, 204 |
| GET / POST | /fields | Lista próprios / cria talhão |
| GET / PUT / DELETE | /fields/{field_id} | Consulta / substitui / exclui próprio |

No Swagger, cadastre e faça login com JSON; copie `access_token`, clique em **Authorize** e informe somente o token. Cada chamada protegida usa `Authorization: Bearer <token>`.

## Segurança e limites

Senhas: PBKDF2-HMAC-SHA256, 600.000 iterações, salt aleatório de 16 bytes e comparação constante. Tokens: aleatórios de 32 bytes, somente SHA-256 persistido, expiração e revogação. Banco: queries parametrizadas, chave estrangeira e área positiva; autorização pelo proprietário em leitura e escrita. Modelo rejeita campos extras, área não finita, negativa ou acima de 100.000 ha. A UI renderiza dados com textContent e guarda token só em memória, não em localStorage. Ao recarregar, exige novo login; a sessão anterior expira em uma hora.

Demonstração local, não serviço pronto para produção: não há HTTPS, rate limiting de login, recuperação de senha, paginação, backup automático nem auditoria centralizada. Antes de expor à rede, adicionar HTTPS, limitação de tentativas, política de cadastro e gestão operacional. Respostas 404 para registros de terceiros evitam revelar sua existência. Não há perfil administrador: autorização é por proprietário.

## Entregáveis e publicação

`relatorio.pdf`, código, testes, OpenAPI, capturas, saída de testes e ZIP local. Repositório: https://github.com/FalcaoOtavio/atividade-pratica-3-arquitetura-apis . O repositório reúne código, documentação e evidências. O enunciado indica 18/11/2026 e entrega para joel.souza@cps.sp.gov.br.
