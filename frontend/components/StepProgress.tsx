// components/StepProgress.tsx
interface StepProgressProps {
  steps: string[]
  current: number // 0-indexed
}

export default function StepProgress({ steps, current }: StepProgressProps) {
  return (
    <div className="flex items-center gap-0 mb-8 bg-white p-4 rounded-xl shadow-sm">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center flex-1 last:flex-none">
          <div className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                i <= current ? 'bg-lawblue text-white' : 'bg-gray-200 text-gray-400'
              }`}
            >
              {i + 1}
            </div>
            <span className={`text-sm font-medium ${i <= current ? 'text-navy' : 'text-gray-400'}`}>
              {step}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mx-3 ${i < current ? 'bg-lawblue' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}