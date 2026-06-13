// frontend/app/login-campus/page.tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { obtenerEstado } from "@/lib/api";

function LoginCampusPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sesionId = searchParams.get("sesion");
  const [mensaje, setMensaje] = useState("Detectando sesión...");

  useEffect(() => {
    if (!sesionId) {
      router.push("/");
      return;
    }

    const intervalo = setInterval(async () => {
      try {
        const estado = await obtenerEstado(sesionId);
        setMensaje(estado.mensaje);

        if (estado.estado === "extrayendo_campus") {
          clearInterval(intervalo);
          router.push(`/progreso-campus?sesion=${sesionId}`);
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
          setMensaje("Error: " + estado.mensaje);
        }
      } catch {
        setMensaje("Error al conectar con el servidor.");
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
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
            mensaje.includes("PAIDEIA") ? "bg-[#10B981] text-white" : "bg-[#2563EB] text-white"
          }`}>
            {mensaje.includes("PAIDEIA") ? "✓" : "1"}
          </div>
          <span className={`text-xs font-medium ${
            mensaje.includes("PAIDEIA") ? "text-[#10B981]" : "text-[#2563EB]"
          }`}>Campus Virtual</span>
        </div>
        <div className={`w-16 h-0.5 mb-4 ${
          mensaje.includes("PAIDEIA") ? "bg-[#10B981]" : "bg-[#D1D5DB]"
        }`} />
        <div className="flex flex-col items-center gap-1">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
            mensaje.includes("PAIDEIA")
              ? "bg-[#2563EB] text-white"
              : "border-2 border-[#D1D5DB] text-[#9CA3AF]"
          }`}>
            2
          </div>
          <span className={`text-xs font-medium ${
            mensaje.includes("PAIDEIA") ? "text-[#2563EB]" : "text-[#9CA3AF]"
          }`}>PAIDEIA</span>
        </div>
      </div>

      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-160px)] gap-6 px-4">
        <div className="w-20 h-20 bg-[#DBEAFE] border border-[#2563EB] rounded-2xl flex items-center justify-center">
          <svg className="w-10 h-10 text-[#2563EB]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>

      <h2 className="text-2xl font-bold text-[#111827]">
        {mensaje.includes("PAIDEIA") ? "Extrayendo datos de PAIDEIA..." :
        mensaje.includes("Campus") && !mensaje.includes("Esperando") ? "Extrayendo datos de Campus Virtual..." :
        "Esperando login en Campus Virtual"}
      </h2>

      <p className="text-[#6B7280] text-sm text-center max-w-md">
        {mensaje.includes("PAIDEIA") 
          ? "El sistema está extrayendo tus actividades académicas de PAIDEIA. Este proceso puede tardar varios minutos."
          : "El navegador se ha abierto en una ventana separada. Ingresa tu usuario y contraseña PUCP en esa ventana. Esta pantalla avanzará automáticamente cuando detecte tu sesión."}
      </p>

        <div className="w-9 h-9 border-4 border-[#DBEAFE] border-t-[#2563EB] rounded-full animate-spin" />

        <p className="text-xs text-[#9CA3AF]">{mensaje}</p>

        <div className="bg-[#DBEAFE] border border-[#2563EB] rounded-lg px-4 py-3 max-w-md">
          <p className="text-xs text-[#1E3A8A]">
            El sistema no almacena tus credenciales. El login ocurre
            directamente en el Campus Virtual.
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

export default function LoginCampus() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F9FAFB]" />}>
      <LoginCampusPage />
    </Suspense>
  );
}