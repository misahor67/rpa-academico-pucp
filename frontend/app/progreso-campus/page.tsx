// frontend/app/progreso-campus/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { obtenerEstado } from "@/lib/api";

type EstadoMes = "pendiente" | "descargando" | "completado" | "existia";

interface MesProgreso {
  nombre: string;
  estado: EstadoMes;
  eventos: number;
}

export default function ProgresoCampus() {
  const router = useRouter();
  const [sesionId, setSesionId] = useState<string | null>(null);
  const [meses, setMeses] = useState<MesProgreso[]>([]);
  const [progreso, setProgreso] = useState(15);
  const [logs, setLogs] = useState<string[]>([]);
  const [cicloInfo, setCicloInfo] = useState("");

  const CICLOS: Record<number, string> = {
    0: "Verano", 1: "Regular 1", 2: "Regular 2"
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("sesion");
    if (!id) { router.push("/"); return; }
    setSesionId(id);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(id);

        // Actualizar meses si el backend los envía
        if (estado.meses_campus && estado.meses_campus.length > 0) {
          setMeses(estado.meses_campus as MesProgreso[]);
        }

        // Actualizar progreso
        if (estado.progreso) setProgreso(estado.progreso);

        // Actualizar logs
        if (estado.logs) setLogs(estado.logs.slice(-5));

        // Actualizar info del ciclo
        if (estado.config) {
          setCicloInfo(`${CICLOS[estado.config.ciclo]} · ${estado.config.anio}`);
        }

        // Navegación según estado
        if (estado.estado === "esperando_confirmacion") {
          clearInterval(intervalo);
          const tienePdfs = estado.pdfs && estado.pdfs.length > 0;
          window.location.href = tienePdfs
            ? `/estado-pdf?sesion=${id}`
            : `/confirmacion?sesion=${id}`;
        }
        if (estado.estado === "extrayendo_paideia" ||
            estado.estado === "esperando_login_paideia") {
          clearInterval(intervalo);
          window.location.href = `/progreso-paideia?sesion=${id}`;
        }
        if (estado.estado === "sincronizando" ||
            estado.estado === "completado") {
          clearInterval(intervalo);
          window.location.href = `/resultado?sesion=${id}`;
        }
        if (estado.estado === "error") {
          clearInterval(intervalo);
          window.location.href = `/resultado?sesion=${id}`;
        }
      } catch {
        console.error("Error al obtener estado");
      }
    }, 1500);

    return () => clearInterval(intervalo);
  }, [router]);

  const completados = meses.filter(m =>
    m.estado === "completado" || m.estado === "existia"
  ).length;

  const iconoEstado = (estado: EstadoMes) => {
    if (estado === "completado" || estado === "existia") return (
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
            {cicloInfo ? `Ciclo ${cicloInfo} · ${meses.length} archivos a procesar` : "Cargando..."}
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
        {meses.length > 0 ? (
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
                  {mes.nombre}
                </span>
                {(mes.estado === "completado" || mes.estado === "existia") && (
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
                {mes.estado === "existia" && (
                  <span className="text-xs bg-[#F3F4F6] text-[#6B7280] px-2 py-1 rounded-full ml-1">
                    En disco
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white border border-[#D1D5DB] rounded-xl p-8 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin" />
            <span className="ml-3 text-sm text-[#6B7280]">Iniciando descarga...</span>
          </div>
        )}

        {/* Log de actividad */}
        {logs.length > 0 && (
          <div className="border border-[#D1D5DB] rounded-xl overflow-hidden">
            <div className="bg-[#F3F4F6] px-4 py-3">
              <span className="text-sm font-semibold text-[#6B7280]">Log de actividad</span>
            </div>
            <div className="bg-[#111827] px-4 py-3 flex flex-col gap-1">
              {logs.map((log, i) => (
                <span key={i} className="text-xs text-[#10B981] font-mono">{log}</span>
              ))}
            </div>
          </div>
        )}

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