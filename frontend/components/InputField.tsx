// components/InputField.tsx
interface InputProps {
  label: string
  placeholder?: string
  type?: string
  value: string
  onChange: (v: string) => void
  error?: string
}

export default function InputField({ label, placeholder, type = 'text', value, onChange, error }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-semibold text-[#444444]">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className={`border rounded-lg px-3 py-2.5 text-sm outline-none
          focus:ring-2 focus:ring-lawblue transition
          ${error ? 'border-red-500' : 'border-gray-300'}
        `}
      />
      {error && <p className="text-red-500 text-xs">{error}</p>}
    </div>
  )
}