// frontend/app/login-paideia/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";

function LoginPaideiaPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");
  const [mensaje, setMensaje] = useState("Detectando sesión...");

  useEffect(() => {
    if (!sesionId) { router.push("/"); return; }

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(sesionId);
        console.log("Estado P6:", estado.estado);

        if (estado.estado === "esperando_confirmacion") {
          clearInterval(intervalo);
          router.push(`/confirmacion?sesion=${sesionId}`);
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

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">
          RPA Académico PUCP
        </span>
      </nav>

      {/* Indicador de pasos */}
      <div className="flex justify-center pt-8 gap-4 items-center">
        <div className="flex flex-col items-center gap-1">
          <div className="w-8 h-8 rounded-full bg-[#10B981] flex items-center justify-center text-white text-sm font-bold">
            ✓
          </div>
          <span className="text-xs text-[#10B981] font-medium">Campus Virtual</span>
        </div>
        <div className="w-16 h-0.5 bg-[#10B981] mb-4" />
        <div className="flex flex-col items-center gap-1">
          <div className="w-8 h-8 rounded-full bg-[#2563EB] flex items-center justify-center text-white text-sm font-bold">
            2
          </div>
          <span className="text-xs text-[#2563EB] font-medium">PAIDEIA</span>
        </div>
      </div>

      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-160px)] gap-6 px-4">
        <div className="w-20 h-20 bg-[#DBEAFE] border border-[#2563EB] rounded-2xl flex items-center justify-center">
          <svg className="w-10 h-10 text-[#2563EB]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>

        <h2 className="text-2xl font-bold text-[#111827]">
          Esperando login en PAIDEIA
        </h2>

        <p className="text-[#6B7280] text-sm text-center max-w-md">
          Ingresa tus credenciales PUCP en la ventana del navegador que se
          abrió. Esta pantalla avanzará automáticamente cuando detecte tu
          sesión.
        </p>

        <div className="w-9 h-9 border-4 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin" />

        <p className="text-xs text-[#9CA3AF]">{mensaje}</p>

        <div className="bg-[#DBEAFE] border border-[#2563EB] rounded-lg px-4 py-3 max-w-md">
          <p className="text-xs text-[#1E3A8A]">
            El sistema no almacena tus credenciales. El login ocurre
            directamente en PAIDEIA.
          </p>
        </div>

        <button
          onClick={() => router.push("/")}
          className="text-sm text-[#6B7280] hover:text-[#374151]"
        >
          Cancelar proceso
        </button>
      </main>
    </div>
  );
}

export default function LoginPaideia() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <LoginPaideiaPage />
    </Suspense>
  );
}