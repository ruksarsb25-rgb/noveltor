import React from "react";

const STEPS = ["Upload", "Metadata", "Sections", "Export"];

export default function Header({ currentStep, onStepClick, onSaveDraft }) {
  return (
    <header className="bg-[#0F3557] text-white px-6 py-3 flex items-center justify-between shadow-lg">
      {/* Logo */}
      <div className="flex items-center gap-2 select-none">
        <div className="w-8 h-8 bg-white rounded flex items-center justify-center">
          <span className="text-[#0F3557] font-black text-lg leading-none">N</span>
        </div>
        <span className="text-white font-semibold tracking-widest text-sm uppercase">
          ovel<span className="text-blue-300"> Future</span>
        </span>
        <span className="text-blue-200 text-xs ml-2 hidden sm:inline">Article Formatter</span>
      </div>

      {/* Step progress */}
      <nav className="flex items-center gap-1">
        {STEPS.map((step, i) => {
          const stepNum = i + 1;
          const isActive = currentStep === stepNum;
          const isDone = currentStep > stepNum;
          const isClickable = isDone || stepNum === currentStep;

          return (
            <React.Fragment key={step}>
              <button
                onClick={() => isClickable && onStepClick(stepNum)}
                disabled={!isClickable}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-all
                  ${isActive ? "bg-white text-[#0F3557]" : ""}
                  ${isDone ? "text-blue-200 hover:text-white cursor-pointer" : ""}
                  ${!isActive && !isDone ? "text-blue-400 cursor-not-allowed" : ""}
                `}
              >
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
                    ${isActive ? "bg-[#0F3557] text-white" : ""}
                    ${isDone ? "bg-blue-400 text-white" : ""}
                    ${!isActive && !isDone ? "bg-blue-800 text-blue-500" : ""}
                  `}
                >
                  {isDone ? "✓" : stepNum}
                </span>
                <span className="hidden sm:inline">{step}</span>
              </button>
              {i < STEPS.length - 1 && (
                <span className="text-blue-600 text-xs">›</span>
              )}
            </React.Fragment>
          );
        })}
      </nav>

      {/* Save draft */}
      <button
        onClick={onSaveDraft}
        className="text-xs border border-blue-400 text-blue-200 hover:bg-blue-800 px-3 py-1.5 rounded transition-colors"
      >
        Save Draft
      </button>
    </header>
  );
}
