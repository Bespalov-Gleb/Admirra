import assert from 'node:assert/strict'
import { test } from 'node:test'
import { trialCard, canOffer, trialDate } from '../src/utils/onboarding.js'
const base = { trial_visible:true, trial_days_left:7, trial_total_days:7, trial_ends_at:'2026-10-02T12:00:00Z',
  projects_count:0,cabinets_count:0,eligible:true,active:false,discount_state:'not_granted' }
test('creation then integration; real date and no modal', () => {
  assert.equal(trialCard(base).action,'Создать проект')
  assert.equal(trialCard({...base,projects_count:1}).action,'Подключить кабинет')
  assert.equal(trialDate(base.trial_ends_at),'2 октября')
  assert.ok(canOffer(base))
})
test('granted wins even if previously connected project deleted', () => {
  const card=trialCard({...base,active:true,discount_state:'granted',expires_at:base.trial_ends_at})
  assert.equal(card.action,'Выбрать тариф');assert.match(card.text,/20% ваша/)
})
test('expired, paid, used and existing accounts never promise a second discount', () => {
  assert.equal(trialCard({...base,trial_visible:false}),null)
  const expired=trialCard({...base,trial_days_left:0,discount_state:'expired'})
  assert.equal(expired.title,'Пробный период закончился');assert.equal(expired.text,'Проекты и настройки сохранены')
  for (const change of [{eligible:false},{discount_state:'used'},{discount_state:'expired'},{cabinets_count:1}]) {
    assert.equal(canOffer({...base,...change}),false)
    assert.doesNotMatch(trialCard({...base,...change}).text,/20%/)
  }
})
test('Russian day inflections and bounded progress', () => {
  for(const [n,text] of [[1,'остался 1 день'],[2,'осталось 2 дня'],[11,'осталось 11 дней'],[21,'остался 21 день']])assert.equal(trialCard({...base,trial_days_left:n}).days,text)
  assert.equal(trialCard({...base,trial_days_left:20}).progress,0)
})
