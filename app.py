import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field

@contextmanager
def db():
    connection = sqlite3.connect(os.getenv('AGRO_DB', 'agro.db'))
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()

@asynccontextmanager
async def lifespan(app):
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, salt TEXT NOT NULL, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS fields (
            id INTEGER PRIMARY KEY, owner INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL, crop TEXT NOT NULL, area_ha REAL NOT NULL CHECK(area_ha>0));''')
    yield

app = FastAPI(title='AgroTalhões', version='1.0.0', description='API REST para gestão de talhões. Cada usuário acessa somente seus registros.', lifespan=lifespan)
bearer = HTTPBearer(auto_error=False)

class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    username: str = Field(min_length=3, max_length=40, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=12, max_length=128)

class UserOut(BaseModel):
    id: int
    username: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int = 3600

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def current_user(auth: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    with db() as c:
        user = c.execute('SELECT users.id,username FROM sessions JOIN users ON users.id=user_id WHERE token_hash=? AND expires>?',
                         (token_hash(auth.credentials), time.time())).fetchone() if auth else None
    if not user:
        raise HTTPException(401, 'Sessão inválida ou expirada', headers={'WWW-Authenticate':'Bearer'})
    return dict(user)

User = Annotated[dict, Depends(current_user)]

@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/', include_in_schema=False)
def index():
    return FileResponse(Path(__file__).with_name('index.html'))

@app.get('/health', tags=['Sistema'])
def health():
    return {'status':'ok'}

@app.post('/auth/register', status_code=201, response_model=UserOut, tags=['Autenticação'])
def register(data: Credentials):
    salt = secrets.token_hex(16)
    hashed = password_hash(data.password, salt)
    try:
        with db() as c:
            cursor = c.execute('INSERT INTO users(username,salt,password_hash) VALUES(?,?,?)', (data.username, salt, hashed))
            return {'id':cursor.lastrowid, 'username':data.username}
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Usuário já cadastrado')

@app.post('/auth/login', response_model=TokenOut, tags=['Autenticação'])
def login(data: Credentials):
    with db() as c:
        user = c.execute('SELECT * FROM users WHERE username=?', (data.username,)).fetchone()
        hashed = password_hash(data.password, user['salt'] if user else '00'*16)
        if not user or not hmac.compare_digest(hashed, user['password_hash']):
            raise HTTPException(401, 'Credenciais inválidas', headers={'WWW-Authenticate':'Bearer'})
        token = secrets.token_urlsafe(32)
        c.execute('DELETE FROM sessions WHERE expires<=?', (time.time(),))
        c.execute('INSERT INTO sessions VALUES(?,?,?)', (token_hash(token), user['id'], time.time()+3600))
    return TokenOut(access_token=token)

@app.get('/auth/me', response_model=UserOut, tags=['Autenticação'])
def me(user: User):
    return user

@app.post('/auth/logout', status_code=204, tags=['Autenticação'])
def logout(user: User, auth: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]):
    with db() as c:
        c.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(auth.credentials),))
    return Response(status_code=204)

class FieldIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=80)
    crop: str = Field(min_length=2, max_length=60)
    area_ha: float = Field(gt=0, le=100000, allow_inf_nan=False)

class FieldOut(FieldIn):
    id: int

def owned(c, field_id, user):
    row = c.execute('SELECT id,name,crop,area_ha FROM fields WHERE id=? AND owner=?', (field_id,user['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Talhão não encontrado')
    return dict(row)

@app.get('/fields', response_model=list[FieldOut], tags=['Talhões'])
def list_fields(user: User):
    with db() as c:
        return [dict(row) for row in c.execute('SELECT id,name,crop,area_ha FROM fields WHERE owner=? ORDER BY id', (user['id'],))]

@app.post('/fields', status_code=201, response_model=FieldOut, tags=['Talhões'])
def create_field(data: FieldIn, user: User, response: Response):
    with db() as c:
        cursor = c.execute('INSERT INTO fields(owner,name,crop,area_ha) VALUES(?,?,?,?)', (user['id'],data.name,data.crop,data.area_ha))
        response.headers['Location'] = f'/fields/{cursor.lastrowid}'
        return owned(c,cursor.lastrowid,user)

@app.get('/fields/{field_id}', response_model=FieldOut, tags=['Talhões'])
def get_field(field_id: int, user: User):
    with db() as c:
        return owned(c,field_id,user)

@app.put('/fields/{field_id}', response_model=FieldOut, tags=['Talhões'])
def update_field(field_id: int, data: FieldIn, user: User):
    with db() as c:
        owned(c,field_id,user)
        c.execute('UPDATE fields SET name=?,crop=?,area_ha=? WHERE id=? AND owner=?', (data.name,data.crop,data.area_ha,field_id,user['id']))
        return owned(c,field_id,user)

@app.delete('/fields/{field_id}', status_code=204, tags=['Talhões'])
def delete_field(field_id: int, user: User):
    with db() as c:
        owned(c,field_id,user)
        c.execute('DELETE FROM fields WHERE id=? AND owner=?', (field_id,user['id']))
    return Response(status_code=204)
