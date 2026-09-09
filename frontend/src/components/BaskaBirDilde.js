import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

// Optional second language for the SAME insight. Shown only when enrichment.used === true,
// always below the untouched core Reveal, collapsed by default. Never a claim about the person.
export const BaskaBirDilde = ({ enrichment }) => {
  const [open, setOpen] = useState(false);
  if (!enrichment?.used) return null;
  return (
    <div data-testid="baska-bir-dilde" className="border-t border-[#E7E0D8] pt-4">
      <button
        type="button"
        data-testid="baska-bir-dilde-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[#57534E] hover:text-[#1A1816]"
      >
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        {enrichment.label_tr || "Başka bir dilde"}
        {enrichment.title && <span className="text-[#8A847C] font-normal">· {enrichment.title}</span>}
      </button>
      {open && (
        <div className="mt-3 rounded-2xl border border-[#E7E0D8] bg-white p-5 space-y-3" data-testid="baska-bir-dilde-body">
          <p className="text-base leading-relaxed text-[#1A1816]">{enrichment.text}</p>
          {enrichment.disclaimer_tr && <p className="text-xs text-[#8A847C]">{enrichment.disclaimer_tr}</p>}
          {enrichment.source_refs?.length > 0 && (
            <p className="text-[11px] font-mono text-[#B8B0A6]">Kaynak: {enrichment.source_refs.slice(0, 3).join(" · ")}</p>
          )}
        </div>
      )}
    </div>
  );
};
