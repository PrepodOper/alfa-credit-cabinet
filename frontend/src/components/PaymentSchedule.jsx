import { useState } from 'react';
import { dateShort, money } from '../lib/format.js';
import Icon from './Icons.jsx';

// Компактные форматы для таблицы: в узкой колонке бэкофиса «97 506 ₽» и
// «24 нояб. 2026 г.» переносятся на две строки и ломают ритм таблицы.
const compactMoney = (value) => money(value, false);
const compactDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' });
};

/**
 * График платежей по кредиту.
 *
 * Показывает сводку (платёж, сумма, переплата, всего к возврату) и таблицу
 * платежей. По умолчанию свёрнут до первых трёх и последнего платежа — на
 * защите не нужно листать 24 строки, но при желании раскрывается целиком.
 */
export default function PaymentSchedule({ schedule, title = 'График платежей', compact = false }) {
  const [expanded, setExpanded] = useState(false);
  if (!schedule?.items?.length) return null;

  const { summary, items } = schedule;
  const preview = items.length > 4 ? [...items.slice(0, 3), ...items.slice(-1)] : items;
  const hidden = items.length - preview.length;

  return (
    <div className="card card-pad">
      <div className="card-head">
        <div>
          <div className="card-title">{title}</div>
          <div className="tiny muted mt-8">
            Аннуитет · {summary.payments_count} платежей · первый {dateShort(summary.first_payment_date)}, последний {dateShort(summary.last_payment_date)}
          </div>
        </div>
        <span className="pill pill-blue"><Icon name="calendar" size={12} /> ежемесячно</span>
      </div>

      <div className={`grid ${compact ? 'grid-2' : 'grid-4'} mt-16`} style={{ gap: 10 }}>
        <div className="metric-mini"><span>Платёж в месяц</span><b style={{ fontSize: 16 }}>{money(summary.monthly_payment)}</b></div>
        <div className="metric-mini"><span>Сумма кредита</span><b style={{ fontSize: 16 }}>{money(summary.amount)}</b></div>
        <div className="metric-mini"><span>Переплата</span><b style={{ fontSize: 16 }}>{money(summary.total_interest)}</b></div>
        <div className="metric-mini"><span>Всего к возврату</span><b style={{ fontSize: 16 }}>{money(summary.total_paid)}</b></div>
      </div>

      <div style={{ overflowX: 'auto', marginTop: 16 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>№</th>
              <th>Дата</th>
              <th style={{ textAlign: 'right' }}>Платёж, ₽</th>
              <th style={{ textAlign: 'right' }}>Проценты, ₽</th>
              <th style={{ textAlign: 'right' }}>Тело долга, ₽</th>
              <th style={{ textAlign: 'right' }}>Остаток, ₽</th>
            </tr>
          </thead>
          <tbody>
            {(expanded ? items : preview).map((row) => (
              <tr key={row.number}>
                <td className="muted" style={{ paddingRight: 4 }}>{row.number}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{compactDate(row.date)}</td>
                <td style={{ textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap' }}>{compactMoney(row.payment)}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }} className="muted">{compactMoney(row.interest)}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{compactMoney(row.principal)}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }} className="muted">{compactMoney(row.balance)}</td>
              </tr>
            ))}
            {!expanded && hidden > 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: 'var(--muted)' }}>
                  … ещё {hidden} {hidden === 1 ? 'платёж' : hidden < 5 ? 'платежа' : 'платежей'} …
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {items.length > 4 && (
        <button className="btn btn-ghost btn-sm mt-12" onClick={() => setExpanded((v) => !v)}>
          <Icon name={expanded ? 'chevronDown' : 'chevronRight'} size={15} />
          {expanded ? 'Свернуть график' : `Показать все ${items.length} платежей`}
        </button>
      )}
    </div>
  );
}
