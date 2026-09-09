import { useCallback, useEffect, useRef, useState } from "react";

// Browser speech input (Web Speech API). No backend. If the browser has no
// SpeechRecognition, `supported` is false and the UI hides the microphone.
export function useSpeechInput({ lang = "tr-TR", onFinal } = {}) {
  const Recognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const supported = Boolean(Recognition);
  const recRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => () => { try { recRef.current?.stop(); } catch { /* noop */ } }, []);

  const start = useCallback(() => {
    if (!supported || listening) return;
    setError(null);
    const rec = new Recognition();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (ev) => {
      let finalText = "";
      let interimText = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i];
        if (r.isFinal) finalText += r[0].transcript;
        else interimText += r[0].transcript;
      }
      setInterim(interimText);
      if (finalText) onFinal?.(finalText.trim());
    };
    rec.onerror = (ev) => { setError(ev.error || "speech_error"); setListening(false); };
    rec.onend = () => { setListening(false); setInterim(""); };
    recRef.current = rec;
    try { rec.start(); setListening(true); } catch (e) { setError("start_failed"); }
  }, [Recognition, supported, listening, lang, onFinal]);

  const stop = useCallback(() => { try { recRef.current?.stop(); } catch { /* noop */ } setListening(false); }, []);

  return { supported, listening, interim, error, start, stop };
}
