import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/Navbar";
import { Landing } from "@/pages/Landing";
import { Anlat } from "@/pages/Anlat";
import { AnlatTurn } from "@/pages/AnlatTurn";
import { Kartlarim } from "@/pages/Kartlarim";

// Public product (launch): /  /anlat  /anlat/:sessionId  /kartlarim
// KENDİNİ BUL (src/pages/Kesfet.js) and the legacy internal views (src/pages/Internal.js, EmployeeVoice,
// ManagerDashboard, PatternRoom, FifthCore) are kept in the codebase but are NOT routed: nothing that is
// unfinished or that carries a deterministic fallback is reachable from a public URL.
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
            <Route path="/kartlarim" element={<Kartlarim />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-[#E7E0D8] py-6 mt-8">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2 text-xs text-[#8A847C]">
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
