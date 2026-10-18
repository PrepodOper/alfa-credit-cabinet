export function money(value, withCurrency = true) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const formatted = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Math.round(value));
  return withCurrency ? `${formatted} ₽` : formatted;
}

export function moneyShort(value) {
  const num = Number(value) || 0;
  if (Math.abs(num) >= 1_000_000) {
    const m = num / 1_000_000;
    return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: m >= 10 ? 0 : 1 }).format(m)} млн ₽`;
  }
  if (Math.abs(num) >= 1000) {
    return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(num / 1000)} тыс. ₽`;
  }
  return `${new Intl.NumberFormat('ru-RU').format(num)} ₽`;
}

export function percent(value) {
  if (value === null || value === undefined) return '—';
  return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 }).format(value)}%`;
}

export function dateShort(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function dateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

export function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'только что';
  if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} дн назад`;
  return dateShort(iso);
}

export const STATUS_META = {
  draft: { label: 'Черновик', tone: 'gray' },
  submitted: { label: 'Отправлена', tone: 'blue' },
  validation: { label: 'Проверка данных', tone: 'blue' },
  scoring: { label: 'Скоринг', tone: 'blue' },
  manual_review: { label: 'Ручное рассмотрение', tone: 'amber' },
  info_requested: { label: 'Нужны уточнения', tone: 'orange' },
  client_info_provided: { label: 'Уточнения получены', tone: 'teal' },
  offer_formed: { label: 'Условия сформированы', tone: 'purple' },
  offer_issued: { label: 'Предложение готово', tone: 'purple' },
  offer_accepted: { label: 'Предложение принято', tone: 'purple' },
  signing: { label: 'Подписание', tone: 'purple' },
  signed: { label: 'Документы подписаны', tone: 'green' },
  funded: { label: 'Кредит выдан', tone: 'green' },
  declined: { label: 'Отказ', tone: 'red' },
  expired: { label: 'Истекло', tone: 'gray' },
};

export function statusMeta(status) {
  return STATUS_META[status] || { label: status, tone: 'gray' };
}

export function plural(n, one, few, many) {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return many;
  if (last > 1 && last < 5) return few;
  if (last === 1) return one;
  return many;
}

export function riskClassLabel(cls) {
  return { A: 'Низкий риск', B: 'Умеренный риск', C: 'Средний риск', D: 'Повышенный риск', E: 'Высокий риск' }[cls] || cls;
}
