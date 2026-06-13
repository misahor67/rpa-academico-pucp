// frontend/app/resultado/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEventos } from "@/lib/api";

function ResultadoPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");
  const [totalEventos, setTotalEventos] = useState(54);

  useEffect(() => {
    if (!sesionId) {
      router.push("/");
      return;
    }
    obtenerEventos(sesionId).then((data) => {
      if (data.total) setTotalEventos(data.total);
    }).catch(() => {});
  }, [sesionId, router]);

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-10 flex flex-col items-center gap-8">

        {/* Icono de exito */}
        <div className="w-20 h-20 bg-[#D1FAE5] border-2 border-[#10B981] rounded-full flex items-center justify-center">
          <svg className="w-10 h-10 text-[#10B981]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <div className="text-center">
          <h1 className="text-3xl font-bold text-[#111827]">
            Sincronizacion completada!
          </h1>
          <p className="text-[#6B7280] mt-2">
            {totalEventos} eventos academicos fueron añadidos exitosamente a tu
            calendario RPA Academico - Regular 2 - 2025
          </p>
        </div>

        {/* Metricas fila 1 */}
        <div className="grid grid-cols-4 gap-4 w-full">
          {[
            { label: "Total insertado", valor: totalEventos, color: "text-[#2563EB]", grande: true },
            { label: "Campus Virtual", valor: 42, color: "text-[#111827]", grande: false },
            { label: "PAIDEIA", valor: 12, color: "text-[#111827]", grande: false },
            { label: "Duracion", valor: "3m 24s", color: "text-[#111827]", grande: false },
          ].map((m, i) => (
            <div key={i} className="bg-white border border-[#D1D5DB] rounded-xl p-5 text-center">
              <p className="text-xs text-[#6B7280] mb-2">{m.label}</p>
              <p className={`font-bold ${m.grande ? "text-3xl" : "text-2xl"} ${m.color}`}>
                {m.valor}
              </p>
            </div>
          ))}
        </div>

        {/* Metricas fila 2 */}
        <div className="grid grid-cols-2 gap-4 w-full">
          {[
            { label: "Ciclo sincronizado", valor: "Regular 2 - 2025" },
            { label: "Fecha y hora", valor: new Date().toLocaleString("es-PE") },
          ].map((m, i) => (
            <div key={i} className="bg-white border border-[#D1D5DB] rounded-xl p-5">
              <p className="text-xs text-[#6B7280] mb-1">{m.label}</p>
              <p className="font-semibold text-[#111827]">{m.valor}</p>
            </div>
          ))}
        </div>

        {/* Pendientes */}
        <div className="w-full bg-[#FEF3C7] border border-[#F59E0B] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[#F59E0B] text-lg">!</span>
            <p className="font-semibold text-[#92400E]">Pendientes de revision manual</p>
          </div>
          <p className="text-sm text-[#92400E] mb-3">
            1 cronograma PDF no pudo procesarse automaticamente.
          </p>
          <div className="bg-white rounded-lg p-3 flex items-center gap-2">
            <div>
              <p className="text-xs font-semibold text-[#111827]">cronograma_MAT301.pdf</p>
              <p className="text-xs text-[#6B7280]">MAT301 - Calculo III</p>
            </div>
          </div>
        </div>

        {/* Botones */}
        <div className="flex gap-3 flex-wrap justify-center">
          
          <button
            onClick={() => window.open("https://calendar.google.com", "_blank")}
            className="bg-[#2563EB] text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-[#1D4ED8]"
            >
            Abrir Google Calendar
          </button>
          <button
            onClick={() => router.push("/configuracion")}
            className="border border-[#2563EB] text-[#2563EB] px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-[#EFF6FF]"
          >
            Nueva sincronizacion
          </button>
          <button
            onClick={() => router.push("/")}
            className="text-[#6B7280] px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-[#F3F4F6]"
          >
            Ver detalle de eventos
          </button>
        </div>
      </main>
    </div>
  );
}

export default function Resultado() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <ResultadoPage />
    </Suspense>
  );
}