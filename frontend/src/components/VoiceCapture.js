import React, { useEffect, useRef, useState } from "react";
import { Mic, Square, ShieldCheck, AlertCircle } from "lucide-react";
import { VOICE } from "../data/copy";

// Uses the browser's own speech recognition. Audio never leaves the device and
// no recording is kept — only the transcript the person confirms is used.
// When the browser has no such support we say so plainly rather than pretending.
const getRecognition = () => {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
};

export const VoiceCapture = ({ onConfirm, onCancel }) => {
  const [supported, setSupported] = useState(true);
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recRef = useRef(null);

  useEffect(() => {
    const rec = getRecognition();
    if (!rec) {
      setSupported(false);
      return;
    }
    rec.lang = "tr-TR";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i += 1) text += e.results[i][0].transcript;
      setTranscript(text);
    };
    rec.onend = () => setRecording(false);
    recRef.current = rec;
    return () => { try { rec.stop(); } catch { /* already stopped */ } };
  }, []);

  if (!supported) {
    return (
      <div className="rounded-2xl border border-[#E7E0D8] bg-white p-5" data-testid="voice-unavailable">
        <div className="flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 text-[#D97706] mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-[#1A1816]">{VOICE.unavailable}</p>
            <p className="mt-1 text-[13px] text-[#8A847C]">{VOICE.unavailableHint}</p>
          </div>
        </div>
        <button onClick={onCancel} className="mt-4 text-sm text-[#C85A32]">Yazarak anlat</button>
      </div>
    );
  }

  const start = () => { setTranscript(""); setRecording(true); try { recRef.current.start(); } catch { /* already running */ } };
  const stop = () => { setRecording(false); try { recRef.current.stop(); } catch { /* already stopped */ } };

  return (
    <div className="rounded-2xl border border-[#E7E0D8] bg-white p-5" data-testid="voice-capture">
      {!transcript && (
        <div className="text-center py-4">
          <button
            data-testid="voice-toggle"
            onClick={recording ? stop : start}
            className={`h-16 w-16 rounded-full flex items-center justify-center mx-auto transition-colors ${
              recording ? "bg-[#C85A32]" : "bg-[#1A1816]"
            }`}
          >
            {recording ? <Square className="h-5 w-5 text-white" /> : <Mic className="h-6 w-6 text-white" />}
          </button>
          <p className="mt-3 text-sm text-[#57534E]">{recording ? VOICE.recording : VOICE.idle}</p>
        </div>
      )}

      {/* transcribe -> show -> edit/confirm -> only then analyze */}
      {transcript && (
        <div data-testid="voice-transcript">
          <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-[#8A847C]">{VOICE.transcriptTitle}</p>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            rows={4}
            className="mt-2 w-full resize-none rounded-xl border border-[#E7E0D8] bg-[#FAF8F5] p-3 text-[15px] leading-relaxed outline-none focus:border-[#C85A32]"
          />
          <p className="mt-1.5 text-[13px] text-[#8A847C]">{VOICE.transcriptHint}</p>
          <div className="mt-3 flex items-center gap-2">
            <button
              data-testid="voice-confirm"
              onClick={() => onConfirm(transcript)}
              className="rounded-full bg-[#1A1816] px-4 py-2 text-sm text-[#FAF8F5]"
            >
              {VOICE.confirm}
            </button>
            <button onClick={() => setTranscript("")} className="text-sm text-[#8A847C]">{VOICE.discard}</button>
          </div>
        </div>
      )}

      <p className="mt-4 flex items-center gap-1.5 text-[11px] text-[#8A847C]">
        <ShieldCheck className="h-3 w-3 text-[#3F6B56]" /> {VOICE.notStored}
      </p>
    </div>
  );
};
