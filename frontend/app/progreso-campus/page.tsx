// frontend/app/progreso-campus/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";

const MESES_REGULAR2 = [
  "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
];

type EstadoMes = "pendiente" | "descargando" | "completado" | "existia";

interface MesProgreso {
  nombre: string;
  estado: EstadoMes;
  eventos: number;
}

function ProgresoCampusPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");

  const [meses, setMeses] = useState<MesProgreso[]>(
    MESES_REGULAR2.map((nombre, i) => ({
      nombre,
      estado: i === 0 ? "completado" : i === 1 ? "completado" : i === 2 ? "descargando" : "pendiente",
      eventos: i === 0 ? 31 : i === 1 ? 28 : 0,
    }))
  );
  const [progreso, setProgreso] = useState(40);
  const [logs, setLogs] = useState([
    "[10:33:21] Navegando a Octubre 2025...",
    "[10:33:22] Descargando archivo .ics...",
    "[10:33:23] Esperando confirmación de descarga...",
  ]);

  useEffect(() => {
    if (!sesionId) {
      router.push("/");
      return;
    }

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(sesionId);

        if (estado.estado === "esperando_confirmacion") {
          clearInterval(intervalo);
          window.location.href = `/confirmacion?sesion=${sesionId}`;
        }
        if (estado.estado === "extrayendo_paideia" ||
            estado.estado === "esperando_login_paideia") {
          clearInterval(intervalo);
          router.push(`/progreso-paideia?sesion=${sesionId}`);
        }
        if (estado.estado === "sincronizando" ||
            estado.estado === "completado") {
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

  const iconoEstado = (estado: EstadoMes) => {
    if (estado === "completado") return (
      <div className="w-6 h-6 rounded-full bg-[#D1FAE5] flex items-center justify-center flex-shrink-0">
        <span className="text-[#10B981] text-xs font-bold">✓</span>
      </div>
    );
    if (estado === "descargando") return (
      <div className="w-6 h-6 border-2 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin flex-shrink-0" />
    );
    return (
      <div className="w-6 h-6 rounded-full border-2 border-[#D1D5DB] flex-shrink-0" />
    );
  };

  const completados = meses.filter(m => m.estado === "completado").length;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
      </nav>

      <main className="max-w-2xl mx-auto px-4 py-8 flex flex-col gap-6">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">
            Extrayendo datos de Campus Virtual
          </h2>
          <p className="text-sm text-[#6B7280] mt-1">
            Ciclo Regular 2 · 2025 · 5 archivos a procesar
          </p>
        </div>

        {/* Barra de progreso */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold text-[#111827]">
              {completados} de {meses.length} meses completados
            </span>
            <span className="text-sm text-[#6B7280]">{progreso}%</span>
          </div>
          <div className="w-full bg-[#E5E7EB] rounded-full h-2">
            <div
              className="bg-[#2563EB] h-2 rounded-full transition-all duration-500"
              style={{ width: `${progreso}%` }}
            />
          </div>
        </div>

        {/* Lista de meses */}
        <div className="bg-white border border-[#D1D5DB] rounded-xl overflow-hidden">
          {meses.map((mes, i) => (
            <div
              key={mes.nombre}
              className={`flex items-center gap-3 px-5 py-4 ${
                i < meses.length - 1 ? "border-b border-[#F3F4F6]" : ""
              } ${mes.estado === "descargando" ? "bg-[#EFF6FF]" : ""}`}
            >
              {iconoEstado(mes.estado)}
              <span className={`text-sm flex-1 font-medium ${
                mes.estado === "descargando" ? "text-[#2563EB]" :
                mes.estado === "pendiente" ? "text-[#9CA3AF]" : "text-[#111827]"
              }`}>
                {mes.nombre} 2025
              </span>
              {mes.estado === "completado" && (
                <span className="text-xs bg-[#D1FAE5] text-[#065F46] px-2 py-1 rounded-full">
                  {mes.eventos} eventos
                </span>
              )}
              {mes.estado === "descargando" && (
                <span className="text-xs bg-[#DBEAFE] text-[#1E3A8A] px-2 py-1 rounded-full">
                  En progreso
                </span>
              )}
              {mes.estado === "pendiente" && (
                <span className="text-xs text-[#9CA3AF]">Pendiente</span>
              )}
            </div>
          ))}
        </div>

        {/* Log de actividad */}
        <div className="border border-[#D1D5DB] rounded-xl overflow-hidden">
          <div className="bg-[#F3F4F6] px-4 py-3 flex justify-between items-center">
            <span className="text-sm font-semibold text-[#6B7280]">
              Log de actividad
            </span>
          </div>
          <div className="bg-[#111827] px-4 py-3 flex flex-col gap-1">
            {logs.map((log, i) => (
              <span key={i} className="text-xs text-[#10B981] font-mono">
                {log}
              </span>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={() => router.push("/")}
            className="text-sm text-[#6B7280] hover:text-[#374151]"
          >
            Cancelar extracción
          </button>
        </div>
      </main>
    </div>
  );
}

export default function ProgresoCampus() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <ProgresoCampusPage />
    </Suspense>
  );
}