import { Check, CheckCircle2 } from 'lucide-react'

interface StepProgressProps {
  steps: string[]
  current: number // 0-indexed
}

export default function StepProgress({ steps, current }: StepProgressProps) {
  return (
    <div className="flex items-center gap-0 mb-8 bg-white/90 p-4 rounded-2xl shadow-sm border border-white/60">
      {steps.map((step, i) => {
        const isCompleted = i < current
        const isActive = i === current
        
        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  isCompleted || isActive 
                    ? 'bg-[#0f305b] text-white shadow-md' 
                    : 'bg-[#e2e8f0] text-[#94a3b8]'
                }`}
              >
                {isCompleted ? <Check size={16} strokeWidth={3} /> : i + 1}
              </div>
              <span className={`text-sm font-bold whitespace-nowrap flex items-center gap-1.5 ${
                isActive ? 'text-[#0f305b]' : isCompleted ? 'text-[#36516e]' : 'text-[#94a3b8]'
              }`}>
                {step}
                {isCompleted && <CheckCircle2 size={16} className="text-emerald-500" />}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="flex-1 px-4">
                <div className={`h-0.5 w-full ${isCompleted ? 'bg-[#0f305b]' : 'bg-[#e2e8f0]'}`} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}