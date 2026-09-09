import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

// Every nested screen shows one of these. Prefers real history (so the browser back stack and
// the router agree); falls back to the parent route when the tab was opened directly.
export const BackLink = ({ to = "/", label = "Geri", testId = "back-link", onBeforeBack }) => {
  const navigate = useNavigate();
  const go = () => {
    onBeforeBack?.();
    if (window.history.state && window.history.state.idx > 0) navigate(-1);
    else navigate(to);
  };
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={go}
      className="inline-flex items-center gap-1.5 text-sm text-[#8A847C] hover:text-[#1A1816] transition-colors"
    >
      <ArrowLeft className="h-4 w-4" /> {label}
    </button>
  );
};
