// frontend/app/progreso-insercion/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";
import { Settings, CheckCircle2, Calendar } from "lucide-react";

function ProgresoInsercionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");

  const [totalEventos, setTotalEventos] = useState(0);
  const [insertados, setInsertados] = useState(0);
  const [ultimoEvento, setUltimoEvento] = useState("");
  const [nombreCalendario, setNombreCalendario] = useState("");
  const [calendarioCreado, setCalendarioCreado] = useState(false);

  useEffect(() => {
    if (!sesionId) { router.push("/"); return; }

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(sesionId);

        if (estado.nombre_calendario) {
          setNombreCalendario(estado.nombre_calendario);
          setCalendarioCreado(true);
        }
        if (estado.insertados !== undefined) setInsertados(estado.insertados);
        if (estado.total_insertar !== undefined) setTotalEventos(estado.total_insertar);
        if (estado.ultimo_evento) setUltimoEvento(estado.ultimo_evento);

        if (estado.estado === "completado") {
          clearInterval(intervalo);
          router.push(`/resultado?sesion=${sesionId}`);
        }
        if (estado.estado === "error") {
          clearInterval(intervalo);
          router.push(`/resultado?sesion=${sesionId}`);
        }
      } catch {
        console.error("Error al obtener estado");
      }
    }, 1500);

    return () => clearInterval(intervalo);
  }, [sesionId, router]);

  const progreso = totalEventos > 0 ? Math.round((insertados / totalEventos) * 100) : 0;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="h-16 bg-[#111827] flex items-center justify-between px-6">
        <span className="text-white font-medium">RPA Académico PUCP</span>
        <Settings className="h-5 w-5 text-white" />
      </nav>

      <main className="flex items-center justify-center min-h-[calc(100vh-64px)] px-4">
        <div className="w-full max-w-[560px] flex flex-col items-center">

          <div className="w-[72px] h-[72px] bg-white border border-gray-200 rounded-2xl shadow-sm flex items-center justify-center">
            <Calendar className="h-9 w-9 text-[#4285F4]" />
          </div>

          <div className="mt-6 text-center">
            <h2 className="text-xl font-semibold text-gray-900">
              Sincronizando con Google Calendar
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              No cierres esta ventana hasta que el proceso termine.
            </p>
          </div>

          {calendarioCreado && (
            <div className="mt-8 w-full bg-[#F0FDF4] rounded-xl px-5 py-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0" />
                <span className="font-semibold text-gray-900">
                  Calendario creado correctamente
                </span>
              </div>
              <p className="mt-1 ml-9 text-sm text-gray-500">
                {nombreCalendario}
              </p>
            </div>
          )}

          <div className="mt-4 w-full bg-[#EFF6FF] border border-[#DBEAFE] rounded-xl px-5 py-4">
            <p className="font-semibold text-[#2563EB]">Insertando eventos...</p>

            <div className="mt-3 w-full h-2.5 bg-[#E5E7EB] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#2563EB] rounded-full transition-all duration-300"
                style={{ width: `${progreso}%` }}
              />
            </div>

            <div className="mt-2 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900">
                {insertados} de {totalEventos} eventos insertados
              </span>
              <span className="text-sm text-gray-500">{progreso}%</span>
            </div>

            {ultimoEvento && (
              <p className="mt-3 text-sm text-gray-500">
                Último insertado: {ultimoEvento}
              </p>
            )}
          </div>

          <p className="mt-8 text-sm text-gray-500 text-center">
            Este proceso puede tardar entre 30 segundos y 2 minutos.
          </p>
        </div>
      </main>
    </div>
  );
}

export default function ProgresoInsercion() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <ProgresoInsercionPage />
    </Suspense>
  );
}