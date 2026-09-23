"""Detached enrichment: provider IO operates on plain data, never a SQL session."""
from lead_validator.config import settings
from lead_validator.services.social_checker import social_checker
from lead_validator.services.social_merge import merge_social_accounts_payload, social_payload_to_json
from lead_validator.services.gosuslugi_checker import gosuslugi_checker
from lead_validator.services.lead_scoring import compute_lead_score


async def enrich(lead, dadata, project, form_data):
    from lead_validator.validators import _restore_name_from_itp_fio, _merge_bool_from_form
    social = None
    if project.enable_social_check:
        social = await social_checker.check_phone(lead.phone, lead.name, lead.email)
    merged, overrides = merge_social_accounts_payload(social, form_data)
    values = {'social_accounts_data': social_payload_to_json(merged)}
    for key in ('has_telegram', 'has_whatsapp', 'has_viber', 'has_tiktok', 'has_vk'):
        values[key] = _merge_bool_from_form(getattr(social, key, None), overrides.get(key))
    if getattr(social, 'itp_email', None) and not lead.email:
        values['email'] = social.itp_email
    if getattr(social, 'itp_name', None):
        values['name'], values['surname'] = _restore_name_from_itp_fio(lead.name, None, social.itp_name)
    if project.enable_gosuslugi_check:
        result = await gosuslugi_checker.check(lead.phone)
        values['has_gosuslugi'] = result.has_registration
        if result.has_registration:
            values['gosuslugi_name'], values['gosuslugi_surname'] = result.name, result.surname
            values['name'] = values.get('name') or lead.name or result.name
            values['surname'] = values.get('surname') or result.surname
    if project.enable_lead_scoring:
        score = compute_lead_score(dadata=dadata,
            **{key: values.get(key) for key in ('has_telegram', 'has_whatsapp', 'has_vk', 'has_viber',
                'has_tiktok', 'has_gosuslugi', 'gosuslugi_name', 'gosuslugi_surname')},
            lead_name=values.get('name') or lead.name, weights=settings)
        values.update(lead_score=score.score, qualification_tier=score.tier)
    return values
