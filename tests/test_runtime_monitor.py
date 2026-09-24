import unittest
from ops.monitoring.check_runtime import ledger_checks,role_checks,EXPECTED_SCHEMA

class RuntimeMonitorTest(unittest.TestCase):
    def test_missing_tick_unknown_outcomes_and_expired_leases_fail_closed(self):
        data=dict(schema=EXPECTED_SCHEMA,scheduler_age=20,expired_leases=0,uncertain=0,report_unknown=0,ai_unknown=0,outbox_wait=1)
        self.assertTrue(all(ledger_checks(data).values()))
        for field,value in [('schema','old'),('scheduler_age',181),('expired_leases',1),('uncertain',1),('report_unknown',1),('ai_unknown',1),('outbox_wait',181)]:
            with self.subTest(field=field):
                self.assertFalse(all(ledger_checks(dict(data,**{field:value})).values()))

    def test_worker_role_is_not_just_a_running_container(self):
        row={'State':{'Running':True,'OOMKilled':False},'Config':{'Env':['APP_PROCESS_ROLE=worker','APP_RELEASE=2ce9513','EXPECTED_SCHEMA_REVISION='+EXPECTED_SCHEMA]}}
        self.assertTrue(role_checks({'reports':row})['reports'])
        self.assertFalse(role_checks({'scheduler':row})['scheduler'])
        row['State']['OOMKilled']=True
        self.assertFalse(role_checks({'reports':row})['reports'])
