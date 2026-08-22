import React, { useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import { Navbar } from "@/components/Navbar";
import { EmployeeVoice } from "@/components/EmployeeVoice";
import { ManagerDashboard } from "@/components/ManagerDashboard";

function App() {
  const [view, setView] = useState("employee");
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="App min-h-screen paper-grain">
      <Navbar view={view} setView={setView} />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {view === "employee" ? (
          <EmployeeVoice onConfirmed={() => setRefreshKey((k) => k + 1)} />
        ) : (
          <ManagerDashboard refreshKey={refreshKey} />
        )}
      </main>
      <footer className="border-t border-[#E7E0D8] py-6 mt-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs text-[#8A847C]">
          <span className="font-serif italic text-sm">Fifthback — sesin duyuldu.</span>
          <span className="font-mono uppercase tracking-[0.16em]">Form yok · Kimlik yok</span>
        </div>
      </footer>
      <Toaster position="bottom-center" richColors closeButton style={{ pointerEvents: "none" }} toastOptions={{ style: { fontFamily: "Plus Jakarta Sans", pointerEvents: "auto" } }} />
    </div>
  );
}

export default App;
