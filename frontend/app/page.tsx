import { Settings } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      {/* Navbar */}
      <nav className="h-16 bg-[#111827] flex items-center justify-between px-6">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
        <button className="text-white hover:text-gray-300 transition-colors">
          <Settings className="h-5 w-5" />
        </button>
      </nav>

      {/* Main Content */}
      <main className="flex flex-col items-center justify-center px-4 py-16">
        {/* Hero Section */}
        <div className="text-center max-w-xl mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4 text-balance">
            Centraliza tu vida académica
          </h1>
          <p className="text-gray-500 text-lg mb-8">
            Sincroniza automáticamente Campus Virtual y PAIDEIA con tu Google Calendar. Sin esfuerzo manual.
          </p>
          <Button className="bg-[#2563EB] hover:bg-[#1d4ed8] text-white px-6 py-2.5 text-base font-medium">
            Iniciar sincronización
          </Button>
        </div>

        {/* Status Card */}
        <div className="w-full max-w-[420px] bg-white border border-gray-200 rounded-xl shadow-sm p-6">
          {/* Last Sync */}
          <div className="mb-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Última sincronización</p>
            <p className="text-gray-900 font-medium">24 de mayo, 2025 — 10:32 am</p>
          </div>

          {/* Ciclo */}
          <div className="flex items-center gap-2 mb-6">
            <span className="text-gray-500">Ciclo:</span>
            <span className="text-gray-900 font-medium">Regular 2 — 2025</span>
          </div>

          {/* Events Count */}
          <div className="text-center mb-6">
            <p className="text-5xl font-bold text-[#2563EB]">54</p>
            <p className="text-gray-500 text-sm mt-1">Eventos insertados</p>
          </div>

          {/* Badges */}
          <div className="flex justify-center gap-2 mb-6">
            <span className="px-3 py-1 bg-blue-100 text-[#2563EB] text-sm font-medium rounded-full">
              Campus Virtual
            </span>
            <span className="px-3 py-1 bg-blue-100 text-[#2563EB] text-sm font-medium rounded-full">
              PAIDEIA
            </span>
          </div>

          {/* History Link */}
          <div className="text-center">
            <a href="#" className="text-[#2563EB] text-sm hover:underline">
              Ver historial
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}
