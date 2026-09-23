export function leadStatus(lead) {
  if (lead.validation_state === 'closed') {
    return { text: 'Закрыта без проверки', className: 'bg-gray-100 text-gray-700' }
  }
  if (lead.validation_state === 'held') {
    return { text: 'Требует сверки', className: 'bg-yellow-100 text-yellow-800' }
  }
  if (lead.status === 'PENDING' || lead.validation_state === 'processing') {
    return { text: 'Проверяется', className: 'bg-blue-100 text-blue-700' }
  }
  return lead.is_accepted
    ? { text: 'Принят', className: 'bg-green-100 text-green-700' }
    : { text: 'Отклонён', className: 'bg-red-100 text-red-700' }
}
