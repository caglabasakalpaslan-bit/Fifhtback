import React from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { WELCOME } from "../data/copy";
import { saveEntryContext } from "../lib/entryContext";

// One short screen, then in. The two context questions that used to sit here
// were removed: nothing in the product reads them, so they cost the person a
// decision before they had seen anything worth deciding about.
// lib/entryContext.js still stores them, ready for a later, better-earned ask.
export const Welcome = ({ onContinue }) => {
  const enter = () => {
    saveEntryContext({});
    onContinue?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="py-20 max-w-lg mx-auto"
      data-testid="welcome-surface"
    >
      <h1 className="font-serif text-4xl sm:text-5xl leading-[1.1] text-[#1A1816]" data-testid="welcome-title">
        {WELCOME.title}
      </h1>

      {WELCOME.body.map((paragraph) => (
        <p key={paragraph.slice(0, 24)} className="mt-6 text-[17px] leading-relaxed text-[#3A3632]">
          {paragraph}
        </p>
      ))}

      <button
        data-testid="welcome-continue"
        onClick={enter}
        className="mt-8 inline-flex items-center gap-1.5 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm text-[#FAF8F5]"
      >
        {WELCOME.cta} <ArrowRight className="h-4 w-4" />
      </button>

      <p className="mt-8 text-[13px] text-[#8A847C]" data-testid="welcome-privacy">{WELCOME.privacy}</p>
    </motion.div>
  );
};
