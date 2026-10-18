import { statusMeta } from '../lib/format.js';

export default function StatusPill({ status, live = false, label }) {
  const meta = statusMeta(status);
  const showPulse = live && ['submitted', 'validation', 'scoring', 'manual_review', 'client_info_provided'].includes(status);
  return (
    <span className={`pill pill-${meta.tone}`}>
      {showPulse ? <span className="pulse-dot" /> : <span className="dot" />}
      {label || meta.label}
    </span>
  );
}
