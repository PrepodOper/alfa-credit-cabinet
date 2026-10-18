import Icon from './Icons.jsx';

const MAP = {
  refresh: 'refresh',
  bolt: 'bolt',
  building: 'building',
  card: 'card',
  wallet: 'wallet',
};

export default function ProductIcon({ icon = 'wallet', size = 44, dark = false }) {
  return (
    <div className={`product-icon ${dark ? 'dark' : ''}`} style={{ width: size, height: size, borderRadius: size * 0.3 }}>
      <Icon name={MAP[icon] || 'wallet'} size={size * 0.5} />
    </div>
  );
}
