// frontend/app/progreso-paideia/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";

interface CursoPaideia {
  titulo: string;
  course_id: string;
  secciones: number;
  entregas: number;
  pdfs: number;
  estado: "completado";
}

interface EstadoPaideia {
  estado: string;
  cursos_paideia: CursoPaideia[];
  total_cursos_paideia: number;
  cursos_completados_paideia: number;
  total_entregas_paideia: number;
  total_pdfs_paideia: number;
  pdfs: { nombre: string; curso: string }[];
  logs: string[];
}

function ProgresoPaideiaPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");

  const [estadoPaideia, setEstadoPaideia] = useState<EstadoPaideia>({
    estado: "extrayendo_paideia",
    cursos_paideia: [],
    total_cursos_paideia: 0,
    cursos_completados_paideia: 0,
    total_entregas_paideia: 0,
    total_pdfs_paideia: 0,
    pdfs: [],
    logs: [],
  });

  useEffect(() => {
    if (!sesionId) {
      router.push("/");
      return;
    }

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(sesionId);
        console.log("Estado P6:", estado.estado);

        // Actualizar datos dinámicos de PAIDEIA
        setEstadoPaideia({
          estado: estado.estado,
          cursos_paideia: estado.cursos_paideia || [],
          total_cursos_paideia: estado.total_cursos_paideia || 0,
          cursos_completados_paideia: estado.cursos_completados_paideia || 0,
          total_entregas_paideia: estado.total_entregas_paideia || 0,
          total_pdfs_paideia: estado.total_pdfs_paideia || 0,
          pdfs: estado.pdfs || [],
          logs: estado.logs || [],
        });

        if (estado.estado === "esperando_confirmacion") {
          clearInterval(intervalo);
          const tienePdfs = estado.pdfs && estado.pdfs.length > 0;
          if (tienePdfs) {
            window.location.href = `/estado-pdf?sesion=${sesionId}`;
          } else {
            window.location.href = `/confirmacion?sesion=${sesionId}`;
          }
        }
        if (estado.estado === "sincronizando" || estado.estado === "completado") {
          clearInterval(intervalo);
          window.location.href = `/resultado?sesion=${sesionId}`;
        }
        if (estado.estado === "error") {
          clearInterval(intervalo);
          window.location.href = `/resultado?sesion=${sesionId}`;
        }
      } catch {
        console.error("Error al obtener estado");
      }
    }, 1500);

    return () => clearInterval(intervalo);
  }, [sesionId, router]);

  const {
    cursos_paideia,
    total_cursos_paideia,
    cursos_completados_paideia,
    total_entregas_paideia,
    total_pdfs_paideia,
    pdfs,
    logs,
  } = estadoPaideia;

  const progreso = total_cursos_paideia > 0
    ? Math.round((cursos_completados_paideia / total_cursos_paideia) * 100)
    : 0;

  // Curso actualmente en progreso: el que sigue al último completado
  const cursoEnProgresoIdx = cursos_completados_paideia;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-[#111827]">
            Extrayendo datos de PAIDEIA
          </h2>
          <p className="text-sm text-[#6B7280] mt-1">
            {total_cursos_paideia > 0
              ? `${total_cursos_paideia} cursos encontrados para el ciclo`
              : "Buscando cursos del ciclo..."}
          </p>
        </div>

        <div className="flex gap-6">
          {/* Columna izquierda */}
          <div className="flex-1 flex flex-col gap-4">
            {/* Barra de progreso */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between">
                <span className="text-sm font-semibold text-[#111827]">
                  {cursos_completados_paideia} de {total_cursos_paideia || "?"} cursos completados
                </span>
                <span className="text-sm text-[#6B7280]">{progreso}%</span>
              </div>
              <div className="w-full bg-[#E5E7EB] rounded-full h-2">
                <div
                  className="bg-[#2563EB] h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progreso}%` }}
                />
              </div>
              {total_cursos_paideia > 0 && (
                <p className="text-xs text-[#6B7280]">
                  {total_cursos_paideia} cursos encontrados para el ciclo
                </p>
              )}
            </div>

            {/* Lista de cursos */}
            <div className="bg-white border border-[#D1D5DB] rounded-xl overflow-hidden">
              {cursos_paideia.length === 0 && total_cursos_paideia === 0 ? (
                /* Estado inicial: aún buscando cursos */
                <div className="px-5 py-6 flex items-center gap-3">
                  <div className="w-6 h-6 border-2 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin flex-shrink-0" />
                  <span className="text-sm text-[#6B7280]">Buscando cursos en PAIDEIA...</span>
                </div>
              ) : (
                <>
                  {/* Cursos ya completados */}
                  {cursos_paideia.map((curso, i) => (
                    <div
                      key={curso.course_id || i}
                      className={`px-5 py-4 ${i < cursos_paideia.length - 1 || cursoEnProgresoIdx < total_cursos_paideia ? "border-b border-[#F3F4F6]" : ""}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full bg-[#D1FAE5] flex items-center justify-center flex-shrink-0">
                          <span className="text-[#10B981] text-xs font-bold">✓</span>
                        </div>
                        <span className="text-sm font-medium flex-1 text-[#111827]">
                          {curso.titulo}
                        </span>
                        <span className="text-xs bg-[#D1FAE5] text-[#065F46] px-2 py-1 rounded-full">
                          Completado
                        </span>
                      </div>
                      <p className="text-xs text-[#6B7280] mt-1 ml-9">
                        {curso.secciones} secciones · {curso.pdfs} PDF{curso.pdfs !== 1 ? "s" : ""} detectado{curso.pdfs !== 1 ? "s" : ""} · {curso.entregas} entrega{curso.entregas !== 1 ? "s" : ""} extraída{curso.entregas !== 1 ? "s" : ""}
                      </p>
                    </div>
                  ))}

                  {/* Curso en progreso (si hay más por procesar) */}
                  {cursoEnProgresoIdx < total_cursos_paideia && (
                    <div className="px-5 py-4 bg-[#EFF6FF] border-b border-[#F3F4F6]">
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 border-2 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin flex-shrink-0" />
                        <span className="text-sm font-medium flex-1 text-[#2563EB]">
                          Procesando curso {cursoEnProgresoIdx + 1}...
                        </span>
                        <span className="text-xs bg-[#DBEAFE] text-[#1E3A8A] px-2 py-1 rounded-full">
                          En progreso
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Cursos pendientes */}
                  {Array.from({
                    length: Math.max(0, total_cursos_paideia - cursoEnProgresoIdx - 1)
                  }).map((_, i) => (
                    <div
                      key={`pendiente-${i}`}
                      className={`px-5 py-4 ${i < total_cursos_paideia - cursoEnProgresoIdx - 2 ? "border-b border-[#F3F4F6]" : ""}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full border-2 border-[#D1D5DB] flex-shrink-0" />
                        <span className="text-sm font-medium flex-1 text-[#9CA3AF]">
                          Curso pendiente
                        </span>
                        <span className="text-xs text-[#9CA3AF]">Pendiente</span>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>

            {/* Log */}
            <div className="border border-[#D1D5DB] rounded-xl overflow-hidden">
              <div className="bg-[#F3F4F6] px-4 py-3">
                <span className="text-sm font-semibold text-[#6B7280]">Log de actividad</span>
              </div>
              <div className="bg-[#111827] px-4 py-3 flex flex-col gap-1 max-h-32 overflow-y-auto">
                {logs.length === 0 ? (
                  <span className="text-xs text-[#6B7280] font-mono">Esperando actividad...</span>
                ) : (
                  logs.map((log, i) => (
                    <span key={i} className="text-xs text-[#10B981] font-mono">{log}</span>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Columna derecha */}
          <div className="w-64 flex flex-col gap-4">
            {/* PDFs detectados */}
            <div className="bg-white border border-[#D1D5DB] rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-[#111827]">
                  Cronogramas PDF
                </span>
                <span className="text-xs bg-[#DBEAFE] text-[#1E3A8A] px-2 py-0.5 rounded-full font-bold">
                  {total_pdfs_paideia}
                </span>
              </div>
              {pdfs.length === 0 ? (
                <p className="text-xs text-[#9CA3AF]">Ninguno detectado aún</p>
              ) : (
                pdfs.map((pdf, i) => (
                  <div key={i} className="flex items-start gap-2 mb-2">
                    <span className="text-red-500 text-sm">📄</span>
                    <div>
                      <p className="text-xs font-semibold text-[#111827]">{pdf.nombre}</p>
                      <p className="text-xs text-[#6B7280]">{pdf.curso}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Entregas extraídas */}
            <div className="bg-white border border-[#D1D5DB] rounded-xl p-5 text-center">
              <p className="text-sm font-semibold text-[#111827] mb-2">
                Entregas extraídas
              </p>
              <p className="text-4xl font-bold text-[#2563EB]">{total_entregas_paideia}</p>
              <p className="text-xs text-[#6B7280] mt-1">de tipo assign (tareas)</p>
            </div>

            {/* Nota */}
            <div className="bg-[#FEF3C7] border border-[#F59E0B] rounded-xl p-4">
              <p className="text-xs text-[#92400E]">
                Solo se extraen actividades tipo entrega (assign). Quizzes y foros no se incluyen.
              </p>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => router.push("/")}
                className="text-sm text-[#6B7280] hover:text-[#374151]"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function ProgresoPaideia() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <ProgresoPaideiaPage />
    </Suspense>
  );
}
