'use client';

import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StepIndicatorProps {
  steps: string[];
  currentStep: number; // 1-based
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="w-full py-6">
      <div className="mx-auto flex max-w-2xl items-center justify-between">
        {steps.map((label, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < currentStep;
          const isActive = stepNum === currentStep;

          return (
            <div key={label} className="flex flex-1 items-center">
              {/* Step circle + label */}
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={cn(
                    'flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors',
                    isCompleted &&
                      'border-green-500 bg-green-500 text-white',
                    isActive &&
                      'border-blue-600 bg-blue-600 text-white shadow-md shadow-blue-600/30',
                    !isCompleted &&
                      !isActive &&
                      'border-gray-300 bg-white text-gray-400'
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    stepNum
                  )}
                </div>
                {/* Label: visible on md+, step number on mobile */}
                <span
                  className={cn(
                    'hidden text-xs font-medium md:block',
                    isActive && 'text-blue-600',
                    isCompleted && 'text-green-600',
                    !isActive && !isCompleted && 'text-gray-400'
                  )}
                >
                  {label}
                </span>
                <span
                  className={cn(
                    'block text-[10px] font-medium md:hidden',
                    isActive && 'text-blue-600',
                    isCompleted && 'text-green-600',
                    !isActive && !isCompleted && 'text-gray-400'
                  )}
                >
                  Step {stepNum}
                </span>
              </div>

              {/* Connecting line (not after last step) */}
              {idx < steps.length - 1 && (
                <div className="mx-2 h-0.5 flex-1">
                  <div
                    className={cn(
                      'h-full rounded-full transition-colors',
                      stepNum < currentStep ? 'bg-green-500' : 'bg-gray-200'
                    )}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
