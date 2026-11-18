import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

class API(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        os.environ['AGRO_DB'] = str(Path(self.tmp.name) / 'test.db')
        import app
        self.app = app
        self.client = TestClient(app.app)
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()
    def login(self, name='agricultor'):
        data = {'username':name, 'password':'SenhaTeste!2026'}
        self.assertEqual(self.client.post('/auth/register', json=data).status_code, 201)
        response = self.client.post('/auth/login', json=data)
        self.assertEqual(response.status_code, 200)
        return {'Authorization':'Bearer ' + response.json()['access_token']}
    def test_auth(self):
        headers = self.login()
        self.assertEqual(self.client.get('/auth/me', headers=headers).json()['username'], 'agricultor')
        self.assertEqual(self.client.get('/auth/me').status_code, 401)
        self.assertEqual(self.client.post('/auth/login', json={'username':'agricultor','password':'SenhaErrada!2026'}).status_code, 401)
        self.assertEqual(self.client.post('/auth/register', json={'username':'agricultor','password':'SenhaTeste!2026'}).status_code, 409)
        self.assertEqual(self.client.post('/auth/register', json={'username':'outro','password':'123'}).status_code, 422)
        self.assertEqual(self.client.post('/auth/logout', headers=headers).status_code, 204)
        self.assertEqual(self.client.get('/auth/me', headers=headers).status_code, 401)
    def test_crud_isolation_validation(self):
        a = self.login()
        b = self.login('vizinho')
        data = {'name':'Talhão Norte','crop':'Milho','area_ha':12.5}
        result = self.client.post('/fields', json=data, headers=a)
        self.assertEqual(result.status_code, 201)
        url = '/fields/' + str(result.json()['id'])
        self.assertEqual(self.client.get(url, headers=a).json()['crop'], 'Milho')
        self.assertEqual(len(self.client.get('/fields', headers=a).json()), 1)
        self.assertEqual(self.client.get('/fields', headers=b).json(), [])
        for method in ('get','put','delete'):
            kwargs = {'json':data} if method=='put' else {}
            self.assertEqual(getattr(self.client,method)(url, headers=b, **kwargs).status_code, 404)
        self.assertEqual(self.client.post('/fields', json=data).status_code, 401)
        self.assertEqual(self.client.post('/fields', json={**data,'area_ha':-1}, headers=a).status_code, 422)
        self.assertEqual(self.client.post('/fields', json={**data,'owner':99}, headers=a).status_code, 422)
        self.assertEqual(self.client.put(url,json={**data,'crop':'Soja'},headers=a).json()['crop'], 'Soja')
        self.assertEqual(self.client.delete(url, headers=a).status_code, 204)
        self.assertEqual(self.client.get(url, headers=a).status_code, 404)
    def test_ui_contract_and_security(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        schema = self.client.get('/openapi.json').json()
        self.assertIn('HTTPBearer', schema['components']['securitySchemes'])
        self.assertIn('security', schema['paths']['/fields']['get'])
        self.assertEqual(self.client.get('/docs').status_code, 200)
        headers = self.login()
        with self.app.db() as c:
            row = c.execute('SELECT * FROM users').fetchone()
            self.assertNotEqual(row['password_hash'], 'SenhaTeste!2026')
            self.assertEqual(len(row['salt']), 32)
            c.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.client.get('/auth/me',headers=headers).status_code, 401)
        self.assertEqual(self.client.get('/health').headers['X-Content-Type-Options'], 'nosniff')
    def test_health(self):
        self.assertEqual(self.client.get('/health').json(), {'status':'ok'})

if __name__ == '__main__':
    unittest.main(verbosity=2)
