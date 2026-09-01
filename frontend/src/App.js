import React, { useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/Navbar";
import { Entry } from "@/surfaces/Entry";
import { EmployeeHome } from "@/surfaces/EmployeeHome";
import { ManagerView } from "@/surfaces/ManagerView";
import { PatternMap } from "@/surfaces/PatternMap";

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
      <Toaster position="bottom-center" richColors closeButton style={{ pointerEvents: "none" }} toastOptions={{ style: { fontFamily: "Plus Jakarta Sans", pointerEvents: "auto" } }} />
    </div>
  );
}

export default App;
