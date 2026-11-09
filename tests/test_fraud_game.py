from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlsplit
import importlib.util
import json
import sqlite3
import unittest
import xml.etree.ElementTree as ET

from app.config import Config
from app.portal import create_app
from app.fraud_game import CASES
from app.fraud_store import database_path
import test_public_game as legacy

Browser = legacy.Browser


class FraudBrowser(Browser):
    def api(self, route, data=None, **kw):
        return self.request('/fraude/api/'+route, data, **kw)


class FraudTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=1793894400.0
        self.config=Config(Path(self.temp.name)/'mia.sqlite3','s'*48,origin='http://localhost:8080')
        self.app=create_app(self.config,clock=lambda:self.now)
        self.b=FraudBrowser(self.app);self.b.session()

    def start(self, tri='ABC', browser=None):
        b=browser or self.b
        self.assertEqual(b.api('claim',{'tri':tri})['status'],200)
        return b.api('start',{})['json']

    def case(self):
        with closing(self.app.fraud.store.connect()) as db:
            row=db.execute('SELECT * FROM games WHERE tri="ABC"').fetchone()
            return CASES[json.loads(row['cases'])[row['card_index']]]

    def answer(self, s, correct=True):
        self.now+=2
        return self.b.api('answer',{'index':s['index'],'review':self.case()['review'] if correct else not self.case()['review']})['json']

    def locate(self, s, hit=True):
        z=self.case()['zones'][0]
        return self.b.api('locate',{'index':s['index'],'panel':z['panel'],'x':z['x']+z['w']/2,'y':z['y']+z['h']/2} if hit else {'index':s['index'],'skip':True})

    def test_full_round_bonus_and_feedback_time_excluded(self):
        s=self.start();seen=[]
        for i in range(6):
            seen.append(s['case']['title']);self.assertEqual(s['phase'],'decision')
            self.assertNotIn('review',s['case']);self.assertNotIn('zones',s['case']);self.assertNotIn('explanation',s['case'])
            s=self.answer(s);self.assertEqual(s['phase'],'locate');self.assertNotIn('feedback',s)
            self.now+=30 # Time spent looking for a bonus never counts.
            r=self.locate(s);self.assertEqual(r['status'],200);s=r['json']
            self.assertTrue(s['feedback']['correct']);self.assertTrue(s['feedback']['hit'])
            self.now+=45 # Neither does time reading the correction.
            if i<5:s=self.b.api('next',{'index':i})['json']
        self.assertEqual(len(set(seen)),6)
        self.assertEqual(s['result'],{'tri':'ABC','score':6,'bonus':6,'timeMs':12000,'grade':'S','total':6})
        self.assertEqual(self.b.api('leaderboard')['json']['rows'],[s['result']])
        self.assertEqual(self.b.session()['json']['participation']['status'],'done')
        self.assertEqual(self.b.api('claim',{'tri':'DEF'})['status'],409)

    def test_retries_resume_every_phase_and_no_double_counting(self):
        self.b.api('claim',{'tri':'ABC'})
        self.assertEqual(self.b.api('claim',{'tri':'ABC'})['status'],200)
        s=self.b.api('start',{})['json'];self.now+=1
        resumed=self.b.api('start',{})['json'];self.assertEqual(resumed['runningMs'],1000)
        decision={'index':0,'review':self.case()['review']}
        s=self.b.api('answer',decision)['json'];self.assertEqual(s['timeMs'],1000)
        self.now+=5
        self.assertEqual(self.b.api('answer',decision)['json'],s)
        self.assertEqual(self.b.api('answer',{**decision,'review':not decision['review']})['status'],409)
        self.assertEqual(self.b.api('start',{})['json'],s)
        r=self.locate(s);self.assertTrue(r['json']['feedback']['hit'])
        self.assertEqual(self.locate(s)['json'],r['json'])
        self.assertEqual(self.b.api('locate',{'index':0,'skip':True})['status'],409)
        self.now+=8;s=self.b.api('next',{'index':0})['json'];self.assertEqual(s['runningMs'],0)
        self.now+=9;s=self.b.api('next',{'index':0})['json'];self.assertEqual(s['runningMs'],9000)
        self.assertEqual(self.b.api('answer',decision)['status'],409)
        # A new worker/process with the same SQLite file resumes the same state.
        other=create_app(self.config,clock=lambda:self.now)
        browser=FraudBrowser(other);browser.cookie=self.b.cookie;browser.csrf=self.b.csrf
        self.assertEqual(browser.api('start',{})['json'],s)

    def test_strict_state_machine_and_coordinates(self):
        self.b.api('claim',{'tri':'ABC'})
        self.assertEqual(self.b.api('answer',{'index':0,'review':True})['status'],409)
        s=self.b.api('start',{})['json']
        self.assertEqual(self.b.api('answer',{'index':0,'review':True})['status'],429)
        for route,body in [('answer',{'index':1,'review':True}),('next',{'index':0}),('locate',{'index':0,'skip':True})]:
            self.assertEqual(self.b.api(route,body)['status'],409)
        self.answer(s)
        bad=[{'index':True,'skip':True},{'index':0,'skip':False},{'index':0,'panel':0,'x':True,'y':.2},
             {'index':0,'panel':99,'x':.2,'y':.2},{'index':0,'panel':0,'x':float('nan'),'y':.2},
             {'index':0,'panel':0,'x':float('inf'),'y':.2},{'index':0,'panel':0,'x':-.1,'y':.2},
             {'index':0,'panel':0,'x':.2,'y':.2,'bonus':6}]
        for body in bad:self.assertEqual(self.b.api('locate',body)['status'],400,body)
        self.assertEqual(self.b.api('answer',{'index':True,'review':True})['status'],400)
        self.assertEqual(self.b.api('answer',{'index':0,'review':1})['status'],400)
        self.assertEqual(self.b.api('result',{'score':6})['status'],404)

    def test_wrong_decisions_and_skipped_bonus_are_not_awarded(self):
        s=self.start()
        for i in range(6):
            s=self.answer(s,correct=False);s=self.locate(s,hit=False)['json']
            self.assertFalse(s['feedback']['correct']);self.assertFalse(s['feedback']['hit'])
            if i<5:s=self.b.api('next',{'index':i})['json']
        self.assertEqual(s['result']['score'],0);self.assertEqual(s['result']['bonus'],0)
        # Final locate/next retries preserve the saved result.
        self.assertEqual(self.b.api('locate',{'index':5,'skip':True})['json'],s)
        self.assertEqual(self.b.api('next',{'index':5})['json'],s)

    def test_cookie_csrf_database_and_leaderboard_isolation(self):
        old=Browser(self.app);old_session=old.session()
        self.assertIn('Path=/recommander;',old_session['headers']['Set-Cookie'])
        self.assertIn('Path=/fraude;',self.b.session()['headers']['Set-Cookie'])
        self.assertNotEqual(self.b.csrf,old.csrf)
        self.assertEqual(old.api('claim',{'tri':'ABC'})['status'],200)
        self.assertEqual(self.b.api('claim',{'tri':'ABC'})['status'],200)
        self.assertEqual(old.api('leaderboard')['json'],{'rows':[]})
        self.assertEqual(self.b.api('leaderboard')['json'],{'rows':[]})
        self.assertEqual(self.b.api('start',{},headers={'HTTP_COOKIE':old.cookie,'HTTP_X_CSRF_TOKEN':old.csrf})['status'],403)
        # Browser sends both cookies; each app selects only its own one.
        both=old.cookie+'; '+self.b.cookie
        self.assertEqual(self.b.api('start',{},headers={'HTTP_COOKIE':both})['status'],200)
        self.assertNotEqual(self.app.recommander.store.path,self.app.fraud.store.path)
        for store in (self.app.recommander.store,self.app.fraud.store):
            with closing(store.connect()) as db:self.assertEqual(db.execute('SELECT tri FROM games').fetchone()[0],'ABC')

    def test_competing_claim_and_expiry(self):
        other=FraudBrowser(self.app);other.session()
        with ThreadPoolExecutor(2) as pool:
            statuses=list(pool.map(lambda b:b.api('claim',{'tri':'123'})['status'],[self.b,other]))
        self.assertEqual(sorted(statuses),[200,409])
        loser=self.b if statuses[0]==409 else other
        self.assertIsNone(loser.session()['json']['participation'])
        self.now+=1801
        self.assertIsNone(self.b.session()['json']['participation'])
        self.assertEqual(self.b.api('claim',{'tri':'123'})['status'],200)

    def test_csrf_host_json_and_explicit_assets(self):
        for headers in [{'HTTP_ORIGIN':'https://evil.test'},{'HTTP_X_CSRF_TOKEN':''},{'HTTP_COOKIE':''},{'HTTP_SEC_FETCH_SITE':'cross-site'}]:
            self.assertEqual(self.b.api('claim',{'tri':'ABC'},headers=headers)['status'],403)
        self.assertEqual(self.b.api('claim',raw=b'x'*1025)['status'],413)
        self.assertEqual(self.b.api('claim',raw=b'nope')['status'],400)
        self.assertEqual(self.b.api('claim',{'tri':'ABC'},headers={'CONTENT_TYPE':'text/plain'})['status'],415)
        self.assertEqual(self.b.request('/fraude',headers={'HTTP_HOST':'evil.test'})['status'],421)
        for path in ['/fraude/../app/fraud_cases.json','/fraude/manifest.json','/fraude/fraud_cases.json','/fraude/data/fraude.sqlite3','/fraudulent','/fraude/api/admin','/fraude/assets/../../app/config.py']:
            self.assertEqual(self.b.request(path)['status'],404,path)
        self.assertEqual(self.b.request('/fraude/')['status'],308)
        self.assertEqual(self.b.request('/fraude',method='HEAD')['body'],b'')
        manifest=json.loads(Path('mia/mia-fraude/manifest.json').read_text())
        for name in manifest:
            response=self.b.request('/fraude/'+name)
            self.assertEqual(response['status'],200,name)
            self.assertGreater(len(response['body']),0)
        self.assertIn(b'game.js?v=',self.b.request('/fraude')['body'])
        script=self.b.request('/fraude/game.js')['body']
        self.assertIn(b'./geometry.js?v=',script)
        self.assertEqual(self.b.request('/fraude/donnees')['status'],200)

    def test_document_updates_are_versioned_without_mutating_case_definitions(self):
        state=self.start()
        for panel in state['case']['panels']:
            url=urlsplit('/fraude/assets/'+panel['src'])
            self.assertRegex(url.query,r'^v=[0-9a-f]{16}$')
            self.assertEqual(self.b.request(url.path)['status'],200)
        self.assertTrue(all('?' not in p['src'] for c in CASES for p in c['panels']))

    def test_shared_wifi_quota_does_not_affect_recommander(self):
        for _ in range(120):self.assertEqual(self.b.api('claim',{'tri':'!'} )['status'],400)
        self.assertEqual(self.b.api('claim',{'tri':'ABC'})['status'],429)
        old=Browser(self.app);old.session();self.assertEqual(old.api('claim',{'tri':'ABC'})['status'],200)

    def test_leaderboard_priority_decisions_then_bonus_then_time(self):
        with self.app.fraud.store.transaction() as db:
            for tri,score,bonus,t in [('AAA',5,6,1),('BBB',6,0,99999),('CCC',6,3,99999),('DDD',6,3,100)]:
                db.execute('INSERT INTO games(tri,owner,cases,created,finished,score,bonus,time_ms,grade) VALUES(?,?,?,?,?,?,?,?,?)',
                           (tri,tri,'[]',self.now,self.now,score,bonus,t,'A'))
        self.assertEqual([r['tri'] for r in self.b.api('leaderboard')['json']['rows']],['DDD','CCC','BBB','AAA'])
        self.now+=31*86400;self.assertEqual(self.b.api('leaderboard')['json']['rows'],[])

    def test_assets_cases_and_zones_are_consistent(self):
        self.assertEqual(len(CASES),6);self.assertEqual(sum(c['review'] for c in CASES),3)
        for case in CASES:
            for panel in case['panels']:
                path=Path('mia/mia-fraude/assets')/panel['src'];self.assertTrue(path.is_file())
                if path.suffix=='.svg':ET.parse(path)
            for z in case['zones']:
                self.assertLess(z['panel'],len(case['panels']))
                for v in ('x','y','w','h'):self.assertTrue(0<=z[v]<=1)
                self.assertLessEqual(z['x']+z['w'],1);self.assertLessEqual(z['y']+z['h'],1)

    def test_failure_containment_and_database_collision(self):
        isolated=create_app(Config(Path(self.temp.name)/'separate.sqlite3','s'*48,origin='http://localhost:8080'))
        with patch('app.fraud_http.load_assets',side_effect=FileNotFoundError('asset missing')):
            with self.assertLogs(level='ERROR'):
                self.assertEqual(FraudBrowser(isolated).request('/fraude')['status'],503)
            self.assertEqual(Browser(isolated).request('/recommander')['status'],200)
            self.assertEqual(Browser(isolated).api('health')['status'],200)
        self.assertEqual(FraudBrowser(isolated).request('/fraude')['status'],200)
        with self.assertRaises(ValueError):database_path(Config(Path(self.temp.name)/'fraude.sqlite3','s'*48))

    def test_replay_is_only_available_in_explicit_local_preview(self):
        self.assertFalse(self.b.session()['json']['preview'])
        self.assertEqual(self.b.api('replay', {})['status'],404)
        self.assertEqual(self.b.request('/fraude/api/replay',{},headers={'QUERY_STRING':'preview=1'})['status'],404)
        from app.fraud_http import FraudApplication
        with self.assertRaises(ValueError):
            FraudApplication(Config(Path(self.temp.name)/'secure.sqlite3','s'*48),preview=True)

    def test_preview_replay_preserves_other_players_and_recommander(self):
        preview=create_app(self.config,preview=True,clock=lambda:self.now)
        b=FraudBrowser(preview);self.assertTrue(b.session()['json']['preview'])
        b.api('claim',{'tri':'ABC'});b.api('start',{})
        # The replay button must also work for sessions that already finished.
        with preview.fraud.store.transaction() as db:
            db.execute('UPDATE games SET finished=?,score=4,bonus=2,time_ms=2000,grade="C" WHERE tri="ABC"',(self.now,))
        self.assertEqual(b.session()['json']['participation']['status'],'done')
        other=FraudBrowser(preview);other.session();other.api('claim',{'tri':'DEF'})
        old=Browser(preview);old.session();old.api('claim',{'tri':'ABC'})
        self.assertEqual(b.api('replay',{},headers={'HTTP_X_CSRF_TOKEN':''})['status'],403)
        self.assertEqual(b.api('replay',{'all':True})['status'],400)
        self.assertEqual(b.api('replay',{})['status'],200)
        self.assertEqual(b.api('replay',{})['status'],200)
        self.assertIsNone(b.session()['json']['participation'])
        self.assertEqual(other.session()['json']['participation']['tri'],'DEF')
        self.assertEqual(old.session()['json']['participation']['tri'],'ABC')
        self.assertEqual(b.api('claim',{'tri':'ABC'})['status'],200)
        self.assertEqual(b.api('start',{})['json']['phase'],'decision')

    def test_backups_cover_both_games_and_restore(self):
        self.start();old=Browser(self.app);old.session();old.api('claim',{'tri':'OLD'})
        spec=importlib.util.spec_from_file_location('host_backup',Path('deploy/backup.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data=Path(self.temp.name)/'production/data';data.mkdir(parents=True)
        for store,name in [(self.app.recommander.store,'mia.sqlite3'),(self.app.fraud.store,'fraude.sqlite3')]:store.backup(data/name)
        module.BASE=Path(self.temp.name);module.BACKUPS=Path(self.temp.name)/'snapshots'
        module.backup();snapshots=list(module.BACKUPS.glob('*.sqlite3'));self.assertEqual(len(snapshots),2)
        for snap in snapshots:
            with closing(sqlite3.connect(snap)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('SELECT tri FROM games').fetchone()[0],'ABC' if '-fraude-' in snap.name else 'OLD')


# Run the existing suite unchanged against the actual mounted application too.
class MountedRecommanderTests(legacy.PublicGameTests):
    def setUp(self):
        super().setUp()
        self.app=create_app(self.app.config,clock=lambda:self.now)
        # Keep existing assertions about the original store/config working.
        self.app.store=self.app.recommander.store
        self.browser=Browser(self.app);self.browser.session()
