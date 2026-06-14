// frontend/app/progreso-paideia/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";

type EstadoCurso = "pendiente" | "en_progreso" | "completado";

interface Curso {
  codigo: string;
  nombre: string;
  estado: EstadoCurso;
  secciones?: string;
  pdfs?: number;
  entregas?: number;
}

function ProgresoPaideiaPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");

  const [cursos] = useState<Curso[]>([
    { codigo: "INF245", nombre: "Bases de Datos Avanzadas", estado: "completado", secciones: "6", pdfs: 1, entregas: 3 },
    { codigo: "MAT301", nombre: "Cálculo III", estado: "en_progreso", secciones: "3 de 5" },
    { codigo: "FIS102", nombre: "Física II", estado: "pendiente" },
    { codigo: "QUI101", nombre: "Química General", estado: "pendiente" },
  ]);

  const [pdfsDetectados] = useState([
    { nombre: "cronograma_INF245.pdf", curso: "Bases de Datos" },
  ]);

  const [entregasExtraidas] = useState(3);

  useEffect(() => {
    if (!sesionId) {
      router.push("/");
      return;
    }

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(sesionId);
        console.log("Estado P6:", estado.estado);

        if (estado.estado === "esperando_confirmacion") {
          clearInterval(intervalo);
          const tienePdfs = estado.pdfs && estado.pdfs.length > 0;
          if (tienePdfs) {
            window.location.href = `/estado-pdf?sesion=${sesionId}`;
          } else {
            window.location.href = `/confirmacion?sesion=${sesionId}`;
          }
        }
        if (estado.estado === "sincronizando" ||
            estado.estado === "completado") {
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

  const completados = cursos.filter(c => c.estado === "completado").length;
  const progreso = Math.round((completados / cursos.length) * 100);

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
          <p className="text-sm text-[#6B7280] mt-1">Ciclo Regular 2 · 2025</p>
        </div>

        <div className="flex gap-6">
          {/* Columna izquierda */}
          <div className="flex-1 flex flex-col gap-4">
            {/* Barra de progreso */}
            <div className="flex flex-col gap-1">
              <div className="flex justify-between">
                <span className="text-sm font-semibold text-[#111827]">
                  {completados} de {cursos.length} cursos completado
                </span>
                <span className="text-sm text-[#6B7280]">{progreso}%</span>
              </div>
              <div className="w-full bg-[#E5E7EB] rounded-full h-2">
                <div
                  className="bg-[#2563EB] h-2 rounded-full transition-all"
                  style={{ width: `${progreso}%` }}
                />
              </div>
              <p className="text-xs text-[#6B7280]">
                {cursos.length} cursos encontrados para el ciclo 2025-2
              </p>
            </div>

            {/* Lista de cursos */}
            <div className="bg-white border border-[#D1D5DB] rounded-xl overflow-hidden">
              {cursos.map((curso, i) => (
                <div
                  key={curso.codigo}
                  className={`px-5 py-4 ${i < cursos.length - 1 ? "border-b border-[#F3F4F6]" : ""} ${
                    curso.estado === "en_progreso" ? "bg-[#EFF6FF]" : ""
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {curso.estado === "completado" && (
                      <div className="w-6 h-6 rounded-full bg-[#D1FAE5] flex items-center justify-center flex-shrink-0">
                        <span className="text-[#10B981] text-xs font-bold">✓</span>
                      </div>
                    )}
                    {curso.estado === "en_progreso" && (
                      <div className="w-6 h-6 border-2 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin flex-shrink-0" />
                    )}
                    {curso.estado === "pendiente" && (
                      <div className="w-6 h-6 rounded-full border-2 border-[#D1D5DB] flex-shrink-0" />
                    )}

                    <span className={`text-sm font-medium flex-1 ${
                      curso.estado === "en_progreso" ? "text-[#2563EB]" :
                      curso.estado === "pendiente" ? "text-[#9CA3AF]" : "text-[#111827]"
                    }`}>
                      {curso.codigo} — {curso.nombre}
                    </span>

                    {curso.estado === "completado" && (
                      <span className="text-xs bg-[#D1FAE5] text-[#065F46] px-2 py-1 rounded-full">
                        Completado
                      </span>
                    )}
                    {curso.estado === "en_progreso" && (
                      <span className="text-xs bg-[#DBEAFE] text-[#1E3A8A] px-2 py-1 rounded-full">
                        Visitando sección {curso.secciones}
                      </span>
                    )}
                    {curso.estado === "pendiente" && (
                      <span className="text-xs text-[#9CA3AF]">Pendiente</span>
                    )}
                  </div>

                  {curso.estado === "completado" && (
                    <p className="text-xs text-[#6B7280] mt-1 ml-9">
                      {curso.secciones} secciones · {curso.pdfs} PDF detectado · {curso.entregas} entregas extraídas
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Log */}
            <div className="border border-[#D1D5DB] rounded-xl overflow-hidden">
              <div className="bg-[#F3F4F6] px-4 py-3">
                <span className="text-sm font-semibold text-[#6B7280]">Log de actividad</span>
              </div>
              <div className="bg-[#111827] px-4 py-3 flex flex-col gap-1">
                <span className="text-xs text-[#10B981] font-mono">[12:34:01] Conectando a PAIDEIA...</span>
                <span className="text-xs text-[#10B981] font-mono">[12:34:03] Sesión iniciada correctamente</span>
                <span className="text-xs text-[#10B981] font-mono">[12:34:05] Navegando a MAT301 — Cálculo III</span>
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
                  {pdfsDetectados.length}
                </span>
              </div>
              {pdfsDetectados.map((pdf, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-red-500 text-sm">📄</span>
                  <div>
                    <p className="text-xs font-semibold text-[#111827]">{pdf.nombre}</p>
                    <p className="text-xs text-[#6B7280]">{pdf.curso}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Entregas extraídas */}
            <div className="bg-white border border-[#D1D5DB] rounded-xl p-5 text-center">
              <p className="text-sm font-semibold text-[#111827] mb-2">
                Entregas extraídas
              </p>
              <p className="text-4xl font-bold text-[#2563EB]">{entregasExtraidas}</p>
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