import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid
from contextlib import contextmanager
import tempfile

sys.path.insert(0, str(Path(__file__).parent))
import notifier as n


class MessageTests(unittest.TestCase):
    def test_real_fields(self):
        text = n.format_message(dict(first_name='Мария', last_name='Тест', email='test@example.com',
            phone='+7 000 000-00-00', providers=['yandex'], registration_utm_source='direct',
            registration_utm_campaign='test', id='test-id'))
        for value in ['Мария Тест', 'test@example.com', '+7 000', 'Яндекс ID', 'direct', 'Кампания: test']:
            self.assertIn(value, text)

    def test_unknown_source_is_not_assumed_direct(self):
        text = n.format_message({})
        self.assertIn('Источник: не определён', text)
        self.assertIn('Телефон: не предоставлен', text)
        self.assertIn('Email подтверждён: нет', text)
        self.assertNotIn('прямой заход', text)

    def test_synthetic_email_is_not_contact(self):
        text = n.format_message({'email': 'max_123@vk-oauth.admirra.ru', 'providers':['max']})
        self.assertIn('Email: не предоставлен', text)
        self.assertIn('Способ: MAX', text)
        self.assertNotIn('max_123', text)

    def test_text_controls_and_size(self):
        text = n.format_message({'username': 'Имя\nПоддельное поле\u202e', 'registration_utm_campaign': 'x'*10000})
        self.assertNotIn('\u202e', text)
        self.assertIn('Имя: Имя Поддельное поле\n', text)
        self.assertLess(len(text), 4096)

    def test_success(self):
        self.assertEqual(n.response_outcome(200, '{"ok":true,"result":{"message_id":42}}'), n.Outcome('sent', message_id=42))

    def test_rate_limit(self):
        out = n.response_outcome(429, '{"ok":false,"error_code":429,"parameters":{"retry_after":180}}')
        self.assertEqual((out.state, out.delay), ('pending', 180))

    def test_ambiguous_results_do_not_replay(self):
        for status, body in [(502,'Bad gateway'), (200,'{}'), (200,'[]'), (500,'{"ok":false,"error_code":500}')]:
            self.assertEqual(n.response_outcome(status,body).state, 'uncertain')

    def test_definite_rejections(self):
        for code in [400,401,403,404]:
            self.assertEqual(n.response_outcome(code,json.dumps({'ok':False,'error_code':code})).state,'failed')

    def test_sender_hides_urls_and_never_retries(self):
        import urllib.error
        with patch.object(n.urllib.request,'build_opener') as make:
            make.return_value.open.side_effect = urllib.error.URLError(TimeoutError('secret URL'))
            result=n.send_message('https://api.telegram.org','123:dummy',-1,'test')
            self.assertEqual(result, n.Outcome('uncertain','transport_error'))
            self.assertEqual(make.return_value.open.call_count,1)

    def test_sender_plaintext_and_fixed_destination(self):
        with patch.object(n.urllib.request,'build_opener') as make:
            response=make.return_value.open.return_value.__enter__.return_value
            response.status=200
            response.read.return_value=b'{"ok":true,"result":{"message_id":1}}'
            n.send_message('https://api.telegram.org','123:dummy',-1,'<b>name</b>')
            request=make.return_value.open.call_args.args[0]
            payload=json.loads(request.data)
            self.assertEqual(payload['chat_id'],-1)
            self.assertNotIn('parse_mode',payload)
            self.assertEqual(payload['text'],'<b>name</b>')
        with self.assertRaises(ValueError):
            n.send_message('https://evil.example','123:dummy',-1,'test')


@unittest.skipUnless(os.getenv('NOTIFIER_TEST_DSN'), 'Requires isolated PostgreSQL')
class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        cls.db=psycopg2.connect(os.environ['NOTIFIER_TEST_DSN'],cursor_factory=RealDictCursor)
        with cls.db, cls.db.cursor() as cur:
            cur.execute('''CREATE TABLE public.users (id uuid PRIMARY KEY, first_name text,
                last_name text, username text, email text, phone text, password_hash text,
                created_at timestamptz DEFAULT now(), email_verified boolean DEFAULT false,
                registration_utm_source text, registration_utm_medium text, registration_utm_campaign text);
                CREATE TABLE public.user_oauth_identities (user_id uuid REFERENCES users(id), provider text,
                    provider_user_id text, created_at timestamptz DEFAULT now());
                CREATE ROLE admirra_registration_notifier NOLOGIN;''')
            cur.execute('INSERT INTO users (id,email) VALUES (%s,%s)',(str(uuid.uuid4()),'old@example.com'))
            cur.execute(Path(__file__).with_name('schema.sql').read_text())
            cur.execute(Path(__file__).with_name('grants.sql').read_text())
            cur.execute('SELECT count(*) AS n FROM registration_notifier.outbox')
            assert cur.fetchone()['n']==0, 'Existing accounts must not be sent'

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        with self.db, self.db.cursor() as cur:
            cur.execute('RESET ROLE; DELETE FROM registration_notifier.outbox')

    def add(self, provider=None):
        uid=str(uuid.uuid4())
        with self.db, self.db.cursor() as cur:
            cur.execute('INSERT INTO public.users (id,email) VALUES (%s,%s)',(uid,'test@example.com'))
            if provider:
                cur.execute('INSERT INTO public.user_oauth_identities (user_id,provider) VALUES (%s,%s)',(uid,provider))
            cur.execute('UPDATE registration_notifier.outbox SET available_at=now() WHERE user_id=%s',(uid,))
        return uid

    def claim(self):
        with self.db, self.db.cursor() as cur:
            cur.execute('SET LOCAL ROLE admirra_registration_notifier')
            return n.claim(self.db)

    def test_all_methods_and_no_duplicate_login(self):
        for provider in [None,'yandex','vk','max']:
            uid=self.add(provider)
            job=self.claim()
            self.assertEqual(str(job['user_id']),uid)
            self.assertEqual(job['user']['providers'],[provider] if provider else [])
            with self.db:
                n.finish(self.db,job,n.Outcome('sent',message_id=42))
            with self.db, self.db.cursor() as cur:
                cur.execute('UPDATE users SET username=%s WHERE id=%s',('Changed',uid))
            self.assertIsNone(self.claim())

    def test_registration_rollback_removes_event(self):
        uid=str(uuid.uuid4())
        with self.db.cursor() as cur:
            cur.execute('INSERT INTO users (id) VALUES (%s)',(uid,))
        self.db.rollback()
        self.assertIsNone(self.claim())

    def test_worker_role_cannot_read_password_or_write_users(self):
        import psycopg2
        for sql in ['SELECT password_hash FROM public.users','UPDATE public.users SET phone=NULL']:
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                with self.db, self.db.cursor() as cur:
                    cur.execute('SET LOCAL ROLE admirra_registration_notifier')
                    cur.execute(sql)

    def test_expired_sending_is_not_retried(self):
        uid=self.add()
        self.claim()
        with self.db, self.db.cursor() as cur:
            cur.execute("UPDATE registration_notifier.outbox SET lease_until=now()-interval '1 second'")
        self.assertIsNone(self.claim())
        with self.db, self.db.cursor() as cur:
            cur.execute('SELECT state FROM registration_notifier.outbox WHERE user_id=%s',(uid,))
            self.assertEqual(cur.fetchone()['state'],'uncertain')

    def test_known_retry_and_max_attempts(self):
        self.add()
        job=self.claim()
        with self.db:
            n.finish(self.db,job,n.Outcome('pending','rate_limit',1))
        self.assertIsNone(self.claim())
        with self.db, self.db.cursor() as cur:
            cur.execute('UPDATE registration_notifier.outbox SET available_at=now(),attempts=11')
        job=self.claim()
        with self.db:
            state=n.finish(self.db,job,n.Outcome('pending','rate_limit',1))
        self.assertEqual(state,'failed')
        self.assertIsNone(self.claim())

    def test_claim_exclusive_and_lease_guard(self):
        self.add()
        job=self.claim()
        self.assertIsNone(self.claim())
        wrong=dict(job,token=str(uuid.uuid4()))
        with self.db:
            n.finish(self.db,wrong,n.Outcome('sent',message_id=12))
        with self.db, self.db.cursor() as cur:
            cur.execute('SELECT state FROM registration_notifier.outbox')
            self.assertEqual(cur.fetchone()['state'],'sending')

    def test_tick_closes_sql_before_http_and_persists_delivery(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        self.add('vk')
        connections=[]
        @contextmanager
        def factory(config):
            db=psycopg2.connect(os.environ['NOTIFIER_TEST_DSN'],cursor_factory=RealDictCursor)
            connections.append(db)
            try:
                with db, db.cursor() as cur:
                    cur.execute('SET LOCAL ROLE admirra_registration_notifier')
                    yield db
            finally:
                db.close()
        def sender(base, token, chat, message):
            self.assertTrue(all(c.closed for c in connections))
            self.assertEqual(chat,-1)
            self.assertIn('VK ID',message)
            return n.Outcome('sent',message_id=99)
        with tempfile.TemporaryDirectory() as temp:
            token=Path(temp)/'token'
            token.write_text('123:dummy')
            config={'token_file':str(token),'api_base':'https://api.telegram.org','chat_id':-1}
            self.assertTrue(n.tick(config,sender=sender,factory=factory))
            self.assertFalse(n.tick(config,sender=sender,factory=factory))
        with self.db, self.db.cursor() as cur:
            cur.execute('SELECT state,message_id FROM registration_notifier.outbox')
            self.assertEqual(dict(cur.fetchone()),{'state':'sent','message_id':99})


if __name__=='__main__':
    unittest.main(verbosity=2)
