import React from "react";
import { RefreshCw } from "lucide-react";

// Honest state when the core cannot produce an answer. No fake question, no fake reveal. The draft is kept.
export const ModelUnavailable = ({ kind = "unavailable", onRetry, retrying, draftKept = true }) => {
  const body = {
    unavailable: "Bağlantı ya da yetki tarafında bir sorun var. Bu senin hikâyenle ilgili değil.",
    bad_output: "Yanıt geldi ama beklenen biçimde değildi. Tekrar denemek genelde yeter.",
    network: "Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.",
    unknown: "Tekrar denemek genelde yeter.",
  }[kind] || "Tekrar denemek genelde yeter.";
  return (
    <div data-testid="model-unavailable" className="rounded-2xl border border-[#E7D6C8] bg-[#FBF3EC] p-5 sm:p-6 space-y-3">
      <p className="font-serif text-2xl leading-snug" data-testid="model-unavailable-title">Şu an yanıt oluşturamıyorum.</p>
      <p className="text-sm text-[#57534E]">{body}{draftKept ? " Yazdıkların duruyor." : ""}</p>
      <button
        type="button"
        data-testid="model-retry"
        disabled={retrying}
        onClick={onRetry}
        className="inline-flex items-center gap-2 rounded-full bg-[#1A1816] px-5 py-2.5 text-sm font-medium text-[#FAF8F5] disabled:opacity-50"
      >
        <RefreshCw className={`h-4 w-4 ${retrying ? "animate-spin" : ""}`} /> Tekrar dene
      </button>
    </div>
  );
};
