// frontend/app/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { verificarBackend, obtenerHistorial, HistorialItem } from "@/lib/api";

const NOMBRES_CICLO: Record<number, string> = {
  0: "Verano",
  1: "Regular 1",
  2: "Regular 2",
};

export default function Home() {
  const router = useRouter();
  const [backendActivo, setBackendActivo] = useState<boolean | null>(null);
  const [historial, setHistorial] = useState<HistorialItem[]>([]);
  const [cargandoHistorial, setCargandoHistorial] = useState(true);

  useEffect(() => {
    verificarBackend().then(setBackendActivo);
    obtenerHistorial()
      .then((data) => setHistorial(data.historial || []))
      .finally(() => setCargandoHistorial(false));
  }, []);

  const ultimaSync = historial.length > 0 ? historial[0] : null;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      {/* Navbar */}
      <nav className="bg-[#111827] h-16 flex items-center justify-between px-8">
        <span className="text-white font-semibold text-lg">
          RPA Académico PUCP
        </span>
        <div className="flex items-center gap-3">
          {backendActivo === null && (
            <span className="text-gray-400 text-sm">Verificando...</span>
          )}
          {backendActivo === true && (
            <span className="text-green-400 text-sm">● Sistema activo</span>
          )}
          {backendActivo === false && (
            <span className="text-red-400 text-sm">● Backend desconectado</span>
          )}
        </div>
      </nav>

      {/* Contenido principal */}
      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-64px)] gap-8 px-4">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-[#111827] mb-3">
            Centraliza tu vida académica
          </h1>
          <p className="text-[#6B7280] text-base max-w-md">
            Sincroniza automáticamente Campus Virtual y PAIDEIA con tu Google
            Calendar. Sin esfuerzo manual.
          </p>
        </div>

        <button
          onClick={() => router.push("/configuracion")}
          className="bg-[#2563EB] text-white px-8 py-3 rounded-lg font-semibold hover:bg-[#1D4ED8] transition-colors"
        >
          Iniciar sincronización
        </button>

        {/* Tarjeta de estado */}
        <div className="bg-white border border-[#D1D5DB] rounded-xl shadow-sm p-6 w-full max-w-md">
          <p className="text-xs text-[#6B7280] mb-1">Última sincronización</p>

          {cargandoHistorial ? (
            <p className="text-[#9CA3AF] text-sm">Cargando historial...</p>
          ) : ultimaSync ? (
            <>
              <p className="text-[#111827] font-medium mb-1">
                {NOMBRES_CICLO[ultimaSync.ciclo] || `Ciclo ${ultimaSync.ciclo}`} · {ultimaSync.anio}
              </p>
              <p className="text-sm text-[#6B7280] mb-3">
                {ultimaSync.total_actividades} actividades sincronizadas
              </p>

              {historial.length > 1 && (
                <div className="border-t border-[#F3F4F6] pt-3 mt-1 flex flex-col gap-2">
                  <p className="text-xs text-[#9CA3AF] font-medium">Historial anterior</p>
                  {historial.slice(1, 4).map((h) => (
                    <div key={h.id_semestre} className="flex justify-between text-sm">
                      <span className="text-[#6B7280]">
                        {NOMBRES_CICLO[h.ciclo] || `Ciclo ${h.ciclo}`} · {h.anio}
                      </span>
                      <span className="text-[#9CA3AF]">{h.total_actividades} eventos</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              <p className="text-[#111827] font-medium mb-3">
                Sin sincronizaciones previas
              </p>
              <p className="text-sm text-[#6B7280]">
                Inicia tu primera sincronización para ver el historial aquí.
              </p>
            </>
          )}
        </div>
      </main>
    </div>
  );
}