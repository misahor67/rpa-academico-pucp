// frontend/app/confirmacion/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado, obtenerEventos, confirmarSincronizacion } from "@/lib/api";

function ConfirmacionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");

  const [nombreCalendario, setNombreCalendario] = useState("");
  const [totalCampus, setTotalCampus] = useState(0);
  const [totalPaideia, setTotalPaideia] = useState(0);
  const [ciclo, setCiclo] = useState("");
  const [confirmando, setConfirmando] = useState(false);
  const [listo, setListo] = useState(false);

  const CICLOS: Record<number, string> = {
    0: "Verano", 1: "Regular 1", 2: "Regular 2"
  };

  useEffect(() => {
    if (!sesionId) { router.push("/"); return; }

    obtenerEstado(sesionId).then((estado) => {
      setTotalCampus(estado.total_campus || 0);
      setTotalPaideia(estado.total_paideia || 0);
      if (estado.config) {
        const nombreCiclo = CICLOS[estado.config.ciclo];
        const anio = estado.config.anio;
        setCiclo(`${nombreCiclo} · ${anio}`);
        setNombreCalendario(`RPA Académico — ${nombreCiclo} · ${anio}`);
      }
      setListo(true);
    });
  }, [sesionId]);

  const handleConfirmar = async () => {
    if (!sesionId || !nombreCalendario) return;
    setConfirmando(true);
    await confirmarSincronizacion(sesionId, nombreCalendario);
    window.location.href = `/progreso-sync?sesion=${sesionId}`;
  };

  if (!listo) return (
    <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
      <p className="text-[#6B7280]">Cargando resumen...</p>
    </div>
  );

  const total = totalCampus + totalPaideia;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
      </nav>

      <main className="max-w-2xl mx-auto px-4 py-8 flex flex-col gap-6">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">
            Resumen de eventos a sincronizar
          </h2>
          <p className="text-sm text-[#6B7280] mt-1">
            Revisa los eventos antes de confirmar la inserción en tu Google Calendar.
          </p>
        </div>

        {/* Métricas */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Campus Virtual", valor: totalCampus, color: "text-[#111827]" },
            { label: "PAIDEIA", valor: totalPaideia, color: "text-[#111827]" },
            { label: "Duplicados", valor: 0, color: "text-[#6B7280]" },
            { label: "Total a insertar", valor: total, color: "text-[#2563EB]", destacado: true },
          ].map((m, i) => (
            <div key={i} className={`bg-white border rounded-xl p-4 text-center ${
              m.destacado ? "border-[#2563EB]" : "border-[#D1D5DB]"
            }`}>
              <p className="text-xs text-[#6B7280] mb-1">{m.label}</p>
              <p className={`text-2xl font-bold ${m.color}`}>{m.valor}</p>
            </div>
          ))}
        </div>

        {/* Nombre del calendario */}
        <div className="bg-white border border-[#D1D5DB] rounded-xl p-5 flex flex-col gap-3">
          <div>
            <label className="text-sm font-semibold text-[#111827]">
              Calendario de destino
            </label>
            <p className="text-xs text-[#6B7280] mt-1">
              El sistema creará un calendario exclusivo para tus actividades
              académicas. No se modificará ningún calendario existente.
            </p>
          </div>
          <input
            type="text"
            value={nombreCalendario}
            onChange={(e) => setNombreCalendario(e.target.value)}
            className="border border-[#D1D5DB] rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-[#2563EB] w-full"
          />
          <p className="text-xs text-[#6B7280]">
            Puedes cambiar el nombre si lo deseas.
          </p>
        </div>

        {/* Nota de seguridad */}
        <div className="bg-[#DBEAFE] border border-[#2563EB] rounded-xl p-4 flex gap-2">
          <span className="text-[#2563EB] text-lg">🛡</span>
          <p className="text-sm text-[#1E3A8A]">
            Tus calendarios actuales no serán modificados. Las actividades
            académicas se insertarán en el calendario indicado arriba.
          </p>
        </div>

        {/* Botones */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={() => router.push("/")}
            className="px-6 py-2.5 rounded-lg text-sm font-semibold border border-[#D1D5DB] text-[#6B7280] hover:bg-[#F3F4F6]"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirmar}
            disabled={confirmando || !nombreCalendario}
            className={`px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-colors ${
              confirmando || !nombreCalendario
                ? "bg-[#D1D5DB] cursor-not-allowed"
                : "bg-[#2563EB] hover:bg-[#1D4ED8]"
            }`}
          >
            {confirmando ? "Confirmando..." : "Confirmar e insertar en Google Calendar"}
          </button>
        </div>
      </main>
    </div>
  );
}

export default function Confirmacion() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <ConfirmacionPage />
    </Suspense>
  );
}