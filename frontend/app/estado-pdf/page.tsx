// frontend/app/estado-pdf/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";
import { Settings, FileText, Check, AlertTriangle, X } from "lucide-react";

function EstadoPDFPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");
  const [pdfs, setPdfs] = useState<any[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    if (!sesionId) { router.push("/"); return; }
    obtenerEstado(sesionId).then((estado) => {
      if (estado.pdfs) setPdfs(estado.pdfs);
      setCargando(false);
    });
  }, [sesionId, router]);

  const procesables = pdfs.filter(p => p.estado === "procesable").length;
  const revision = pdfs.filter(p => p.estado === "revision").length;
  const errores = pdfs.filter(p => p.estado === "error").length;

  const handleContinuar = () => {
    router.push(`/confirmacion?sesion=${sesionId}`);
  };

  if (cargando) return (
    <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
      <p className="text-[#6B7280]">Cargando...</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="h-16 bg-[#111827] flex items-center justify-between px-6">
        <span className="text-white font-semibold text-lg">RPA Académico PUCP</span>
        <button className="text-white hover:text-gray-300">
          <Settings className="w-5 h-5" />
        </button>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-1">
            Estado de cronogramas PDF
          </h2>
          <p className="text-gray-500 text-sm">
            {pdfs.length} {pdfs.length === 1 ? "archivo detectado" : "archivos detectados"} en tus cursos de PAIDEIA
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {pdfs.length === 0 && (
            <div className="bg-white border border-[#D1D5DB] rounded-xl p-8 text-center">
              <p className="text-[#6B7280]">No se detectaron cronogramas PDF en tus cursos.</p>
            </div>
          )}

          {pdfs.map((pdf, i) => {
            const esVerde = pdf.estado === "procesable";
            const esAmarillo = pdf.estado === "revision";
            const esRojo = pdf.estado === "error";
            return (
              <div key={i} className={`bg-white rounded-xl p-5 border ${
                esVerde ? "border-[#10B981]" :
                esAmarillo ? "border-[#F59E0B]" : "border-[#EF4444]"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      esVerde ? "bg-[#D1FAE5]" :
                      esAmarillo ? "bg-[#FEF3C7]" : "bg-[#FEE2E2]"
                    }`}>
                      <FileText className={`w-5 h-5 ${
                        esVerde ? "text-[#10B981]" :
                        esAmarillo ? "text-[#F59E0B]" : "text-[#EF4444]"
                      }`} />
                    </div>
                    <span className="font-semibold text-gray-900">{pdf.nombre}</span>
                  </div>
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                    esVerde ? "bg-[#D1FAE5] text-[#059669]" :
                    esAmarillo ? "bg-[#FEF3C7] text-[#92400E]" :
                    "bg-[#FEE2E2] text-[#DC2626]"
                  }`}>
                    {esVerde ? "Procesable" : esAmarillo ? "Requiere revisión manual" : "Error de descarga"}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-3 ml-[52px]">
                  Curso: {pdf.curso}
                </p>
                <div className={`rounded-lg p-3 ml-[52px] ${
                  esVerde ? "bg-[#F0FDF4]" :
                  esAmarillo ? "bg-[#FEF3C7]" : "bg-[#FEE2E2]"
                }`}>
                  <p className={`text-sm flex items-center gap-1.5 ${
                    esVerde ? "text-[#15803D]" :
                    esAmarillo ? "text-[#92400E]" : "text-[#DC2626]"
                  }`}>
                    {esVerde && <Check className="w-4 h-4" />}
                    {esAmarillo && <AlertTriangle className="w-4 h-4" />}
                    {esRojo && <X className="w-4 h-4" />}
                    {pdf.mensaje}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {pdfs.length > 0 && (
          <div className="bg-[#F3F4F6] rounded-lg p-4 mt-6">
            <div className="flex items-center justify-center gap-4 text-sm">
              <span className="text-[#15803D] font-medium">{procesables} procesado{procesables !== 1 ? "s" : ""} automáticamente</span>
              <div className="w-px h-4 bg-gray-400" />
              <span className="text-[#D97706] font-medium">{revision} requiere{revision !== 1 ? "n" : ""} revisión</span>
              <div className="w-px h-4 bg-gray-400" />
              <span className="text-[#DC2626] font-medium">{errores} con error</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-50"
          >
            Ver detalle completo
          </button>
          <button
            onClick={handleContinuar}
            className="px-4 py-2.5 bg-[#2563EB] text-white rounded-lg font-medium text-sm hover:bg-[#1D4ED8]"
          >
            Continuar
          </button>
        </div>
      </main>
    </div>
  );
}

export default function EstadoPDF() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <EstadoPDFPage />
    </Suspense>
  );
}