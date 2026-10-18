const RISK_COLORS = {
  A: '#0E9F6E',
  B: '#65a30d',
  C: '#D97706',
  D: '#EA580C',
  E: '#DC2626',
};

export default function ScoreRing({ score = 0, riskClass = 'C', size = 84, stroke = 7, light = false, max = 1000 }) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = Math.max(0, Math.min(1, score / max));
  const color = RISK_COLORS[riskClass] || '#D97706';
  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={light ? 'rgba(255,255,255,0.16)' : '#EEF0F4'} strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={`${circumference * filled} ${circumference}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <div className="val" style={{ color: light ? '#fff' : 'var(--ink)' }}>{score}</div>
    </div>
  );
}

export { RISK_COLORS };
