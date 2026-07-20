// components/Button.tsx
interface ButtonProps {
  label: string
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'gold'
  disabled?: boolean
  loading?: boolean
}

export default function Button({ label, onClick, variant = 'primary', disabled, loading }: ButtonProps) {
  const styles = {
    primary: 'bg-navy text-white hover:bg-lawblue',
    secondary: 'bg-white text-navy border border-navy hover:bg-lblue',
    gold: 'bg-gold text-navy hover:opacity-90 font-bold',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition ${styles[variant]} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      }`}
    >
      {loading ? 'Loading...' : label}
    </button>
  )
}