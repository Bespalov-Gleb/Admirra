"""Isolated mobile layout regression checks. No real account or production API calls.

Run Vite with WW_TEST=1 VITE_DEV_SKIP_AUTH=true on port 5199, then run this script.
Requires Python Playwright and installed Google Chrome. Screenshots go to /tmp.
"""
import json, os
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

BASE=os.environ.get('ADMIRRA_MOBILE_QA_URL','http://127.0.0.1:5199')
assert urlparse(BASE).hostname in ('localhost','127.0.0.1'), 'Use an isolated local instance'
OUT=os.environ.get('ADMIRRA_MOBILE_QA_OUTPUT','/private/tmp/admirra-mobile-qa')
os.makedirs(OUT,exist_ok=True)
P={'id':'p1','name':'КТК / China Today','description':'Автотовары · Москва','display_id':100091,'is_active':True,'integrations':[{'id':'i1','platform':'YANDEX','is_connected':True,'balance':128400},{'id':'i2','platform':'VK','is_connected':True,'balance':58000}]}
PROJECTS=[P,{**P,'id':'p2','name':'Очень длинное название проекта / Иркутск / Газобетон','description':''}]
PREV={'expenses':170000,'leads':123,'clicks':5942,'impressions':220000,'cpa':1382,'cpc':28.6,'cost_by_platform':{'yandex':90000,'vk':80000}}
SUMMARY={'expenses':170452,'impressions':168432,'clicks':3856,'leads':59,'cr':1.53,'cpa':2889,'cpc':44.20,'balance':105245,'leads_available':True,'leads_configured':True,'cost_by_platform':{'YANDEX':86434,'VK':84018},'trends':{'expenses':-45,'leads':-52,'cpa':15,'cr':-26,'impressions':-20,'clicks':-35,'cpc':12},'prev':PREV}
CAMPAIGNS=[{'id':str(i),'name':f'Газобетон | Поиск / Иркутск {i}','platform':'YANDEX','cost':7000+i*50,'impressions':17000,'clicks':540,'cpc':13.5,'ctr':3.17,'conversions':4,'cpa':1750,'is_active':True,'has_children':True,'trend_cost':-15,'trend_conversions':20,'trend_cpa':-4} for i in range(1,9)]
DIRECTIONS={'enabled':True,'mode':'cards','label':'Услуги','label_key':'services','items':[{'id':'d1','name':'Газобетон','campaign_count':4,'campaign_ids':['1','2','3','4'],'expenses':86434,'leads':34,'cpl':2542,'budget_share':50.7},{'id':'d2','name':'Строительство','campaign_count':4,'campaign_ids':['5','6','7','8'],'expenses':84018,'leads':25,'cpl':3360,'budget_share':49.3}]}
PLAN={'expenses':{'reference':'План 300 000 ₽','actual':170452,'target':300000,'elapsed_fraction':.7},'leads':{'reference':'План 300','actual':59,'target':300,'elapsed_fraction':.7},'cpa':{'reference':'Цель 1 000 ₽','actual':860,'target':1000}}
requests=[]
def respond(route):
    if not urlparse(route.request.url).path.startswith('/api/'):
        route.continue_(); return
    path=urlparse(route.request.url).path.replace('/api/v1','').replace('/api','')
    requests.append(path)
    query=parse_qs(urlparse(route.request.url).query)
    data=[]
    if path.rstrip('/')=='/clients': data=PROJECTS
    elif path=='/auth/me':data={'id':'qa','first_name':'Тим','email':'qa@example.test'}
    elif 'folders/tree' in path:data={'folders':[],'root_projects':PROJECTS}
    elif 'directions' in path:data=DIRECTIONS
    elif 'dashboard/summary' in path:
        data=SUMMARY
        ch=query.get('platform',query.get('channel',['all']))[0]
        if ch in ['yandex','vk','avito']:
            expense={'yandex':86434,'vk':84018,'avito':0}[ch]
            leads={'yandex':14,'vk':45,'avito':0}[ch]
            data={**SUMMARY,'expenses':expense,'leads':leads,'clicks':1928,'cost_by_platform':{ch:expense},'balance':128400 if ch=='yandex' else 58000}
            if query.get('client_id',[''])[0]=='p2':data['balance']=0 if ch=='yandex' else None
    elif 'dynamics' in path:data={'labels':['Пн','Вт','Ср','Чт','Пт','Сб','Вс'],'costs':[1800,3400,4300,4100,7000,9600,8600],'impressions':[2000]*7,'clicks':[150]*7,'conversions':[3,7,5,9,8,11,16],'cpa':[600]*7,'cpc':[12]*7}
    elif 'dashboard/goals' in path:
        vk=query.get('platform',query.get('channel',['']))[0]=='vk'
        zero=query.get('client_id',[''])[0]=='p2'
        data=[{'id':'g1','name':'Заявка отправлена','count':0 if zero else (45 if vk else 14),'prev_count':60 if vk else 63,'prev_cost':80000 if vk else 90000,'cost':84018 if vk else 86434,'summable':True,'trend':-10}]
    elif 'campaigns' in path:data=CAMPAIGNS
    elif 'integrations' in path and 'sync' not in path:data=[{**x,'client_id':'p1','platform':'yandex_direct' if x['platform']=='YANDEX' else 'vk_ads','status':'connected'} for x in P['integrations']]
    elif 'detector' in path and 'cross' in path:data={'items':[]}
    elif 'detector' in path:data={'enabled':True,'warmup_status':'ready','alerts':[],'metric_plan':PLAN,'plan_warmup_status':False,'onboarding_dismissed':True}
    elif 'notifications' in path:data={'items':[],'unread_count':0} if 'unread' in path else []
    elif 'sync' in path:data={'items':[],'integrations':[],'jobs':[]}
    elif 'settings' in path:data={}
    elif 'comment' in path:data={'text':'Период ровный, заявки держатся у цели.','lead':'Период ровный, заявки держатся у цели.','body':['Основной объём заявок даёт поиск.'],'recommendation':'Стоит сохранить текущие настройки.','generated_at':'2026-09-11T03:02:00Z'}
    route.fulfill(status=200,content_type='application/json',body=json.dumps(data))

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':393,'height':852},device_scale_factor=1,is_mobile=True,has_touch=True)
    page.add_init_script("sessionStorage.setItem('auth_token','mobile-qa');localStorage.setItem('currentProjectId','p1')")
    page.route('**/api/**',respond)
    page.route('https://**',lambda route:route.abort())
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    for path,name in [('/project-card','projects'),('/dashboard/general-3?client_id=p1','dashboard')]:
        page.goto(BASE+path)
        page.wait_for_timeout(2000)
        page.screenshot(path=f'{OUT}/{name}.png',full_page=True)
        for pos in [600,1200,1800,2400]:
            page.locator('main').evaluate('(e,y)=>e.scrollTop=y',pos)
            page.wait_for_timeout(150)
            page.screenshot(path=f'{OUT}/{name}-{pos}.png')
        page.locator('main').evaluate('(e)=>e.scrollTop=0')
        print(name,page.url,page.locator('body').inner_text()[:500])
        print('errors',errors)
    failures=[]
    def check(label, ok):
        print(('PASS ' if ok else 'FAIL ')+label)
        if not ok:failures.append(label)
    known_errors = {"Cannot read properties of null (reading 'classList')", 'Swiper is not defined'}
    check('no new runtime errors', all(e in known_errors for e in errors))
    for width in [320,393,430,660,1440]:
        page.set_viewport_size({'width':width,'height':852})
        for path,name in [('/project-card','projects'),('/dashboard/general-3?client_id=p1','dashboard')]:
            page.goto(BASE+path);page.wait_for_timeout(700)
            check(f'{name} {width} main width',page.locator('main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
            if width<700:
                total=page.locator('.app-header').bounding_box()['height']+page.locator('.mw-slice').bounding_box()['height']
                check(f'{name} {width} sticky height',abs(total-(94 if name=='projects' else 96))<1)
                page.locator('main').evaluate('e=>e.scrollTop=600');page.wait_for_timeout(100)
                check(f'{name} {width} sticky stays',abs(page.locator('.mw-slice').bounding_box()['y']-48)<1)
                page.locator('main').evaluate('e=>e.scrollTop=0');page.wait_for_timeout(100)
                page.screenshot(path=f'{OUT}/{name}-{width}.png')
                if name=='projects':
                    zero=page.locator('.mw-project').nth(1)
                    check(f'zero leads CPL {width}',zero.locator('.mw-project-kpi').first.locator('strong').inner_text()=='—')
                    check(f'zero leads CR {width}','0,00%' in zero.locator('.mw-project-kpi').nth(3).inner_text())
                    check(f'zero leads reason {width}','нет лидов за период' in zero.inner_text())
                    check(f'unknown balance is not zero {width}','—' in zero.locator('.mw-balances>span').nth(1).inner_text())
                if name=='dashboard':
                    check(f'trend readable {width}',page.locator('.metric-card .trend').first.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)>=13'))
                    check(f'KPI pair {width}',abs(page.locator('[data-metric="leads"]').bounding_box()['y']-page.locator('[data-metric="cpa"]').bounding_box()['y'])<1)
                overflow=page.locator('.mw-project-kpi>strong,.metric-text>strong').evaluate_all('nodes=>nodes.filter(e=>e.getBoundingClientRect().width>0 && e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)')
                check(f'{name} {width} numbers fit',not overflow)
                if overflow:print('overflow',overflow)
            else:
                check(f'{name} desktop mobile hidden',not page.locator('.mw-slice').is_visible())
    page.set_viewport_size({'width':393,'height':852})
    page.goto(BASE+'/project-card');page.wait_for_timeout(500)
    page.locator('.mw-period-pill').click()
    check('period sheet opens',page.get_by_role('dialog',name='Период и суммы').is_visible())
    page.get_by_role('checkbox',name='Цены с НДС 22%').uncheck()
    check('VAT does not close sheet',page.get_by_role('dialog').is_visible())
    page.get_by_role('button',name='Закрыть',exact=True).click()
    check('VAT suffix amber',page.locator('.mw-period-pill--net').is_visible())
    page.locator('.mw-period-pill').click();page.get_by_role('button',name='Указать период',exact=True).click()
    check('calendar 42 dates',page.locator('.mw-calendar button').count()==42)
    page.get_by_role('button',name='Сбросить',exact=True).click()
    check('incomplete range disabled',not page.get_by_role('button',name='Применить',exact=True).is_enabled())
    page.locator('.mw-calendar button:not(.outside)').nth(2).click();page.locator('.mw-calendar button:not(.outside)').nth(8).click()
    page.screenshot(path=f'{OUT}/calendar.png')
    page.get_by_role('button',name='Применить',exact=True).click();page.wait_for_timeout(200)
    check('custom range closes sheet',page.get_by_role('dialog').count()==0)
    check('custom date label', '3 – 9' in page.locator('.mw-period-pill').inner_text())
    page.get_by_role('button',name='Поиск проектов',exact=True).click();page.get_by_role('textbox',name='Поиск проектов').fill('China')
    check('project search',page.locator('.mw-project').count()==1)
    page.get_by_role('button',name='Закрыть поиск').click();page.locator('.mw-project').first.get_by_role('button',name='Аналитика',exact=True).click();page.wait_for_timeout(500)
    check('SPA header context survives',page.locator('.mw-back').is_visible())
    page.get_by_role('button',name='Фильтры услуг и кампаний').click()
    page.get_by_role('checkbox',name='Все услуги').uncheck()
    check('empty selection cannot show all projects',not page.get_by_role('button',name='Показать',exact=True).is_enabled())
    page.get_by_role('checkbox',name='Газобетон',exact=False).check()
    page.get_by_role('button',name='Кампании',exact=False).click()
    check('direction limits campaigns',page.locator('.mw-check').count()==5)
    page.screenshot(path=f'{OUT}/filters.png')
    page.get_by_role('button',name='Показать',exact=True).click();page.wait_for_timeout(400)
    check('filter dot visible',page.locator('.mw-filter i').is_visible())
    page.get_by_role('button',name='Фильтры услуг и кампаний').click()
    check('direction selection survives reopen',page.get_by_role('checkbox',name='Газобетон',exact=False).is_checked() and not page.get_by_role('checkbox',name='Строительство',exact=False).is_checked())
    page.get_by_role('button',name='Закрыть',exact=True).click()
    page.locator('main').evaluate('e=>e.scrollTop=0');page.wait_for_timeout(200)
    check('returns to start',page.locator('.mw-project-heading').bounding_box()['y']>=96)
    page.get_by_role('button',name='Фильтры услуг и кампаний').click();page.get_by_role('button',name='Сбросить',exact=True).click();page.get_by_role('button',name='Показать',exact=True).click();page.wait_for_timeout(200)
    page.locator('.chart-area').scroll_into_view_if_needed();page.locator('.chart-area').tap(position={'x':170,'y':80})
    check('chart touch tooltip',page.locator('.chart-tooltip').count()>0)
    for width in [320,393]:
        page.set_viewport_size({'width':width,'height':852});page.goto(BASE+'/project-card');page.wait_for_timeout(400)
        page.evaluate("document.documentElement.style.fontSize='84.375%'")
        check(f'large text {width} page width',page.locator('main').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
        check(f'large text {width} title fits',page.locator('.mw-scope-label').bounding_box()['y']>=0)
        page.screenshot(path=f'{OUT}/large-text-{width}.png')
    reference=browser.new_page(viewport={'width':1500,'height':1000})
    reference.route('https://**',lambda route:route.abort())
    for file,name in [('/tmp/admirra_mobile_tz.html','reference-project'),('/tmp/admirra_mobile_dashboard_tz.html','reference-dashboard')]:
        if os.path.isfile(file):
            reference.goto('file://'+file);reference.wait_for_timeout(100)
            mockup=reference.locator('.mk').filter(has_text='Сводный CPL').first if name=='reference-project' else reference.locator('.mk').first
            mockup.screenshot(path=f'{OUT}/{name}.png')
    print('FAILURES',failures)
    browser.close()
    if failures:raise SystemExit(1)
