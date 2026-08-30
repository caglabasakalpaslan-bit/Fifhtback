import React, { useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/Navbar";
import { Entry } from "@/surfaces/Entry";
import { EmployeeHome } from "@/surfaces/EmployeeHome";
import { ManagerView } from "@/surfaces/ManagerView";
import { PatternMap } from "@/surfaces/PatternMap";
import { BRAND } from "@/data/copy";

function App() {
  const [view, setView] = useState("entry");
  const [homeKey, setHomeKey] = useState(0);

  const handleSaved = (target) => {
    setHomeKey((k) => k + 1);
    if (target === "home") setView("home");
  };

  return (
    <div className="App min-h-screen paper-grain">
      <Navbar view={view} setView={setView} />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {view === "entry" && <Entry onSaved={handleSaved} />}
        {view === "home" && <EmployeeHome key={homeKey} onStart={() => setView("entry")} />}
        {view === "manager" && <ManagerView />}
        {view === "patterns" && <PatternMap />}
      </main>
      <footer className="border-t border-[#E7E0D8] py-6 mt-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs text-[#8A847C]">
          <span className="font-serif italic text-sm">{BRAND.name} — {BRAND.line}</span>
          <span className="font-mono uppercase tracking-[0.16em]">Form yok · Kimlik yok</span>
        </div>
      </footer>
      <Toaster position="bottom-center" richColors closeButton style={{ pointerEvents: "none" }} toastOptions={{ style: { fontFamily: "Plus Jakarta Sans", pointerEvents: "auto" } }} />
    </div>
  );
}

export default App;
