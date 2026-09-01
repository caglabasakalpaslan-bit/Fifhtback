import React, { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ArrowRight } from "lucide-react";
import { WELCOME } from "../data/copy";
import { saveEntryContext } from "../lib/entryContext";

// One calm screen, shown once, before "Söyle".
// Typography carries the hierarchy so the copy can grow or shrink without the
// layout turning into a wall: lead paragraph first, the rest quieter.
const Choice = ({ label, active, onClick, testId }) => (
  <button
    type="button"
    data-testid={testId}
    aria-pressed={active}
    onClick={onClick}
    className={`rounded-full border px-4 py-2 text-sm transition-colors ${
      active
        ? "border-[#1A1816] bg-[#1A1816] text-[#FAF8F5]"
        : "border-[#E7E0D8] bg-white text-[#57534E] hover:border-[#C9C0B6]"
    }`}
  >
    {label}
  </button>
);

export const Welcome = ({ onContinue }) => {
  const [answers, setAnswers] = useState({});

  const pick = (key, value) =>
    setAnswers((a) => ({ ...a, [key]: a[key] === value ? null : value }));

  const commit = () => {
    saveEntryContext({ experience: answers.experience ?? null, leads: answers.leads ?? null });
    onContinue?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="py-14 max-w-xl mx-auto"
      data-testid="welcome-surface"
    >
      <h1 className="font-serif text-4xl sm:text-5xl leading-[1.08] text-[#1A1816]" data-testid="welcome-title">
        {WELCOME.title}
      </h1>

      <div className="mt-6 space-y-4">
        {WELCOME.body.map((paragraph, i) => (
          <p
            key={paragraph.slice(0, 24)}
            className={
              i === 0
                ? "text-[17px] leading-relaxed text-[#3A3632]"
                : "text-[15px] leading-relaxed text-[#57534E]"
            }
          >
            {paragraph}
          </p>
        ))}
      </div>

      <div className="mt-10 border-t border-[#E7E0D8] pt-8 space-y-6" data-testid="welcome-questions">
        {WELCOME.questions.map((q) => (
          <div key={q.key}>
            <p className="text-[15px] text-[#1A1816]">{q.label}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {q.options.map((opt) => (
                <Choice
                  key={opt}
                  label={opt}
                  active={answers[q.key] === opt}
                  onClick={() => pick(q.key, opt)}
                  testId={`welcome-${q.key}-option`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-6 text-[13px] leading-relaxed text-[#8A847C]">{WELCOME.support}</p>

      <p className="mt-4 flex items-start gap-1.5 text-[13px] leading-relaxed text-[#8A847C]" data-testid="welcome-privacy">
        <ShieldCheck className="h-3.5 w-3.5 mt-[3px] shrink-0 text-[#3F6B56]" />
        <span>{WELCOME.privacy}</span>
      </p>

      <button
        data-testid="welcome-continue"
        onClick={commit}
        className="mt-8 inline-flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5]"
      >
        {WELCOME.cta} <ArrowRight className="h-4 w-4" />
      </button>
    </motion.div>
  );
};
