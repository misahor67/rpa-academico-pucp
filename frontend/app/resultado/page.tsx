// frontend/app/resultado/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEventos, obtenerEstado, type EstadoSesion } from "@/lib/api";

type CambioNuevo = NonNullable<EstadoSesion["cambios_detectados"]>["nuevas"][number];
type CambioModificado = NonNullable<EstadoSesion["cambios_detectados"]>["modificadas"][number];

function ResultadoPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");

  const [totalEventos, setTotalEventos] = useState(0);
  const [campus, setCampus] = useState(0);
  const [paideia, setPaideia] = useState(0);
  const [ciclo, setCiclo] = useState("");
  const [nombreCalendario, setNombreCalendario] = useState("RPA Académico PUCP");
  const [fechaHora, setFechaHora] = useState("");
  const [estado, setEstado] = useState("completado");
  const [cambiosNuevas, setCambiosNuevas] = useState<CambioNuevo[]>([]);
  const [cambiosModificadas, setCambiosModificadas] = useState<CambioModificado[]>([]);

  const CICLOS: Record<number, string> = {
    0: "Verano", 1: "Regular 1", 2: "Regular 2"
  };

  const formatearFechaHora = (iso: string) => {
    try {
      const fecha = new Date(iso);
      return fecha.toLocaleString("es-PE", {
        day: "numeric",
        month: "long",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  useEffect(() => {
    if (!sesionId) { router.push("/"); return; }

    setFechaHora(new Date().toLocaleString("es-PE"));

    obtenerEstado(sesionId).then((data) => {
      setEstado(data.estado);
      setCampus(data.total_campus || 0);
      setPaideia(data.total_paideia || 0);
      setTotalEventos((data.total_campus || 0) + (data.total_paideia || 0));
      if (data.nombre_calendario) setNombreCalendario(data.nombre_calendario);
      if (data.config) {
        setCiclo(`${CICLOS[data.config.ciclo]} · ${data.config.anio}`);
      }
      if (data.cambios_detectados) {
        setCambiosNuevas(data.cambios_detectados.nuevas || []);
        setCambiosModificadas(data.cambios_detectados.modificadas || []);
      }
    });
  }, [sesionId]);

  const hayError = estado === "error";

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-10 flex flex-col items-center gap-8">

        {/* Icono */}
        <div className={`w-20 h-20 rounded-full flex items-center justify-center border-2 ${
          hayError
            ? "bg-[#FEE2E2] border-[#EF4444]"
            : "bg-[#D1FAE5] border-[#10B981]"
        }`}>
          {hayError ? (
            <span className="text-[#EF4444] text-3xl font-bold">!</span>
          ) : (
            <svg className="w-10 h-10 text-[#10B981]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>

        <div className="text-center">
          <h1 className="text-3xl font-bold text-[#111827]">
            {hayError ? "Error en la sincronización" : "Sincronizacion completada!"}
          </h1>
          <p className="text-[#6B7280] mt-2">
            {hayError
              ? "Ocurrió un error durante el proceso. Intenta de nuevo."
              : `${totalEventos} eventos academicos fueron añadidos a tu calendario "${nombreCalendario}"`
            }
          </p>
        </div>

        {!hayError && (
          <>
            {/* Metricas fila 1 */}
            <div className="grid grid-cols-4 gap-4 w-full">
              {[
                { label: "Total insertado", valor: totalEventos, color: "text-[#2563EB]", grande: true },
                { label: "Campus Virtual", valor: campus, color: "text-[#111827]", grande: false },
                { label: "PAIDEIA", valor: paideia, color: "text-[#111827]", grande: false },
                { label: "Fecha", valor: fechaHora.split(",")[0] || "", color: "text-[#111827]", grande: false },
              ].map((m, i) => (
                <div key={i} className="bg-white border border-[#D1D5DB] rounded-xl p-5 text-center">
                  <p className="text-xs text-[#6B7280] mb-2">{m.label}</p>
                  <p className={`font-bold ${m.grande ? "text-3xl" : "text-xl"} ${m.color}`}>
                    {m.valor}
                  </p>
                </div>
              ))}
            </div>

            {/* Metricas fila 2 */}
            <div className="grid grid-cols-2 gap-4 w-full">
              <div className="bg-white border border-[#D1D5DB] rounded-xl p-5">
                <p className="text-xs text-[#6B7280] mb-1">Ciclo sincronizado</p>
                <p className="font-semibold text-[#111827]">{ciclo || "Cargando..."}</p>
              </div>
              <div className="bg-white border border-[#D1D5DB] rounded-xl p-5">
                <p className="text-xs text-[#6B7280] mb-1">Hora de finalización</p>
                <p className="font-semibold text-[#111827]">{fechaHora}</p>
              </div>
            </div>
            {/* Cambios detectados respecto a la sincronización anterior */}
            {(cambiosNuevas.length > 0 || cambiosModificadas.length > 0) && (
              <div className="w-full bg-[#FFFBEB] border border-[#FDE68A] rounded-xl p-5">
                <p className="font-semibold text-sm text-[#92400E] mb-3">
                  Cambios detectados respecto a tu última sincronización
                </p>
                <div className="flex flex-col gap-4">
                  {cambiosNuevas.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-[#92400E] mb-2">
                        {cambiosNuevas.length} actividad{cambiosNuevas.length > 1 ? "es" : ""} nueva{cambiosNuevas.length > 1 ? "s" : ""}
                      </p>
                      <div className="flex flex-col gap-2">
                        {cambiosNuevas.slice(0, 5).map((c, i) => (
                          <div key={i} className="bg-white border border-[#FDE68A] rounded-lg px-3 py-2">
                            <p className="text-sm font-medium text-[#111827]">{c.nombre}</p>
                            <p className="text-xs text-[#6B7280] mt-0.5">
                              {c.curso} · {c.fuente} · {formatearFechaHora(c.fecha)}
                            </p>
                          </div>
                        ))}
                        {cambiosNuevas.length > 5 && (
                          <p className="text-xs text-[#92400E]">y {cambiosNuevas.length - 5} más...</p>
                        )}
                      </div>
                    </div>
                  )}
                  {cambiosModificadas.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-[#92400E] mb-2">
                        {cambiosModificadas.length} actividad{cambiosModificadas.length > 1 ? "es" : ""} con fecha modificada
                      </p>
                      <div className="flex flex-col gap-2">
                        {cambiosModificadas.slice(0, 5).map((c, i) => (
                          <div key={i} className="bg-white border border-[#FDE68A] rounded-lg px-3 py-2">
                            <p className="text-sm font-medium text-[#111827]">{c.nombre}</p>
                            <p className="text-xs text-[#6B7280] mt-0.5">
                              {c.curso} · {c.fuente}
                            </p>
                            <p className="text-xs text-[#6B7280] mt-1">
                              <span className="line-through">{formatearFechaHora(c.fecha_anterior)}</span>
                              {" → "}
                              <span className="font-medium text-[#92400E]">{formatearFechaHora(c.fecha_nueva)}</span>
                            </p>
                          </div>
                        ))}
                        {cambiosModificadas.length > 5 && (
                          <p className="text-xs text-[#92400E]">y {cambiosModificadas.length - 5} más...</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Botones */}
        <div className="flex gap-3 flex-wrap justify-center">
          {!hayError && (
            <button
              onClick={() => window.open("https://calendar.google.com", "_blank")}
              className="bg-[#2563EB] text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-[#1D4ED8]"
            >
              Abrir Google Calendar
            </button>
          )}
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
            Volver al inicio
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