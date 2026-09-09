import React from "react";
import { RefreshCw } from "lucide-react";

// Honest state when the core cannot reach the model. No fake question, no fake reveal.
export const ModelUnavailable = ({ kind = "unavailable", onRetry, retrying, draftKept = true }) => {
  const copy = {
    unavailable: { title: "Model şu an erişilemiyor.", body: "Bağlantı ya da yetki tarafında bir sorun var. Bu senin hikâyenle ilgili değil." },
    bad_output: { title: "Çekirdek bu kez düzgün cevap veremedi.", body: "Model yanıt verdi ama beklenen biçimde değil. Tekrar denemek genelde yeter." },
    network: { title: "Sunucuya ulaşılamadı.", body: "Ağ bağlantısını kontrol edip tekrar dene." },
    unknown: { title: "Bir şey ters gitti.", body: "Tekrar denemek genelde yeter." },
  }[kind] || { title: "Bir şey ters gitti.", body: "" };
  return (
    <div data-testid="model-unavailable" className="rounded-2xl border border-[#E7D6C8] bg-[#FBF3EC] p-6 space-y-3">
      <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-[#B04D27] font-semibold">Erişilemedi</p>
      <p className="font-serif text-2xl leading-snug">{copy.title}</p>
      <p className="text-sm text-[#57534E]">{copy.body}{draftKept ? " Yazdıkların duruyor." : ""}</p>
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
