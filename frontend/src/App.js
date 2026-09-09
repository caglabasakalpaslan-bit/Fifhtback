import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/Navbar";
import { Landing } from "@/pages/Landing";
import { Anlat } from "@/pages/Anlat";
import { AnlatTurn } from "@/pages/AnlatTurn";
import { Kesfet, KesfetWorld } from "@/pages/Kesfet";
import { InternalLayout, InternalIndex } from "@/pages/Internal";
import { FifthCore } from "@/components/FifthCore";
import { EmployeeVoice } from "@/components/EmployeeVoice";
import { ManagerDashboard } from "@/components/ManagerDashboard";
import { PatternRoom } from "@/components/PatternRoom";

// Public: /  /anlat  /anlat/:sessionId  /kesfet  /kesfet/:worldId
// Internal (unlinked): /internal/*
function App() {
  return (
    <BrowserRouter>
      <div className="App min-h-screen paper-grain flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/anlat" element={<Anlat />} />
            <Route path="/anlat/:sessionId" element={<AnlatTurn />} />
            <Route path="/kesfet" element={<Kesfet />} />
            <Route path="/kesfet/:worldId" element={<KesfetWorld />} />
            <Route path="/internal" element={<InternalLayout />}>
              <Route index element={<InternalIndex />} />
              <Route path="fifth" element={<FifthCore />} />
              <Route path="calisan-sesi" element={<EmployeeVoice onConfirmed={() => {}} />} />
              <Route path="yonetici" element={<ManagerDashboard refreshKey={0} />} />
              <Route path="pattern-room" element={<PatternRoom />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-[#E7E0D8] py-6 mt-8">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs text-[#8A847C]">
            <span className="font-serif italic text-sm">Fifthback — sesin duyuldu.</span>
            <span className="font-mono uppercase tracking-[0.16em]">Form yok · Kimlik yok</span>
          </div>
        </footer>
        <Toaster position="bottom-center" richColors closeButton style={{ pointerEvents: "none" }} toastOptions={{ style: { fontFamily: "Plus Jakarta Sans", pointerEvents: "auto" } }} />
      </div>
    </BrowserRouter>
  );
}

export default App;
