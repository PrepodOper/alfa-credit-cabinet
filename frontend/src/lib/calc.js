export function annuity(amount, annualRate, months) {
  const r = annualRate / 100 / 12;
  if (!amount || !months) return 0;
  if (r === 0) return amount / months;
  return (amount * r) / (1 - Math.pow(1 + r, -months));
}

export function totalInterest(amount, annualRate, months) {
  return annuity(amount, annualRate, months) * months - amount;
}

export function termOptions(product) {
  const min = product.min_term_months;
  const max = product.max_term_months;
  const step = max - min <= 12 ? 3 : max - min <= 30 ? 6 : 12;
  const opts = [];
  for (let t = min; t <= max; t += step) opts.push(t);
  if (opts[opts.length - 1] !== max) opts.push(max);
  return opts;
}

export function clampAmount(product, value) {
  return Math.min(product.max_amount, Math.max(product.min_amount, value));
}
