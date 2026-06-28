// frontend/app/configuracion/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { iniciarSincronizacion } from "@/lib/api";

const CICLOS = [
  { id: 0, nombre: "Verano", meses: "Ene · Feb · Mar" },
  { id: 1, nombre: "Regular 1", meses: "Mar · Abr · May · Jun · Jul" },
  { id: 2, nombre: "Regular 2", meses: "Ago · Sep · Oct · Nov · Dic" },
];

const OPCIONES_RECORDATORIO = [
  { id: "ninguno", minutos: null, label: "Sin recordatorio" },
  { id: "30min", minutos: 30, label: "30 minutos antes" },
  { id: "1h", minutos: 60, label: "1 hora antes" },
  { id: "1d", minutos: 1440, label: "1 día antes" },
];

export default function Configuracion() {
  const router = useRouter();
  const [cicloSeleccionado, setCicloSeleccionado] = useState<number | null>(null);
  const [anio, setAnio] = useState(new Date().getFullYear());
  const [fuente, setFuente] = useState<string | null>(null);
  const [recordatorioId, setRecordatorioId] = useState<string>("ninguno");
  const [cargando, setCargando] = useState(false);

  const formCompleto = cicloSeleccionado !== null && fuente !== null;

  const handleContinuar = async () => {
    if (!formCompleto) return;
    setCargando(true);
    try {
      const recordatorioSeleccionado = OPCIONES_RECORDATORIO.find((o) => o.id === recordatorioId);
      const config = {
        ciclo: cicloSeleccionado!,
        anio,
        campus: fuente === "campus" || fuente === "ambas",
        paideia: fuente === "paideia" || fuente === "ambas",
        recordatorio_minutos: recordatorioSeleccionado?.minutos ?? null,
      };
      const respuesta = await iniciarSincronizacion(config);
      // Navegar a la pantalla de login con el ID de sesión
      const siguientePantalla = fuente === "paideia" ? "login-paideia" : "login-campus";
      router.push(`/${siguientePantalla}?sesion=${respuesta.sesion_id}&fuente=${fuente}`);
    } catch (error) {
      console.error("Error al iniciar sincronización:", error);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      {/* Navbar */}
      <nav className="bg-[#111827] h-16 flex items-center px-8">
        <span className="text-white font-semibold text-lg">
          RPA Académico PUCP
        </span>
      </nav>

      {/* Breadcrumb */}
      <div className="max-w-2xl mx-auto px-4 pt-6">
        <p className="text-xs text-[#6B7280]">Inicio &gt; Configurar sincronización</p>
      </div>

      {/* Contenido */}
      <main className="max-w-2xl mx-auto px-4 py-6 flex flex-col gap-8">
        <h1 className="text-2xl font-bold text-[#111827]">
          Configurar sincronización
        </h1>

        {/* Sección 1 — Año */}
        <section className="flex flex-col gap-3">
          <label className="font-semibold text-sm text-[#111827]">
            Año del ciclo
          </label>
          <input
            type="number"
            value={anio}
            onChange={(e) => setAnio(Number(e.target.value))}
            className="w-40 border border-[#D1D5DB] rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-[#2563EB]"
          />
        </section>

        {/* Sección 2 — Ciclo */}
        <section className="flex flex-col gap-3">
          <label className="font-semibold text-sm text-[#111827]">
            Ciclo académico
          </label>
          <div className="flex gap-4">
            {CICLOS.map((ciclo) => (
              <button
                key={ciclo.id}
                onClick={() => setCicloSeleccionado(ciclo.id)}
                className={`flex-1 border rounded-xl p-4 text-left transition-all ${
                  cicloSeleccionado === ciclo.id
                    ? "border-[#2563EB] bg-[#EFF6FF]"
                    : "border-[#D1D5DB] bg-white"
                }`}
              >
                <p className={`font-semibold text-sm ${cicloSeleccionado === ciclo.id ? "text-[#2563EB]" : "text-[#111827]"}`}>
                  {ciclo.nombre}
                </p>
                <p className={`text-xs mt-1 ${cicloSeleccionado === ciclo.id ? "text-[#2563EB]" : "text-[#6B7280]"}`}>
                  {ciclo.meses}
                </p>
              </button>
            ))}
          </div>
        </section>

        {/* Sección 3 — Fuentes */}
        <section className="flex flex-col gap-3">
          <label className="font-semibold text-sm text-[#111827]">
            Fuentes de extracción
          </label>
          <div className="flex flex-col gap-3">
            {[
              { id: "ambas", label: "Ambas plataformas", desc: "Campus Virtual y PAIDEIA" },
              { id: "campus", label: "Solo Campus Virtual", desc: "Solo el calendario del Campus Virtual" },
              { id: "paideia", label: "Solo PAIDEIA", desc: "Solo entregas y cronogramas de PAIDEIA" },
            ].map((op) => (
              <button
                key={op.id}
                onClick={() => setFuente(op.id)}
                className="flex items-start gap-3 text-left"
              >
                <div className={`mt-0.5 w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
                  fuente === op.id ? "border-[#2563EB]" : "border-[#D1D5DB]"
                }`}>
                  {fuente === op.id && (
                    <div className="w-2 h-2 rounded-full bg-[#2563EB]" />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-[#111827]">{op.label}</p>
                  <p className="text-xs text-[#6B7280]">{op.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* Sección 4 — Recordatorio */}
        <section className="flex flex-col gap-3">
          <label className="font-semibold text-sm text-[#111827]">
            Recordatorio en Google Calendar
          </label>
          <p className="text-xs text-[#6B7280]">
            Cada actividad sincronizada incluirá una notificación popup en Google Calendar con la anticipación que elijas.
          </p>
          <div className="flex gap-3 flex-wrap">
            {OPCIONES_RECORDATORIO.map((op) => (
              <button
                key={op.id}
                onClick={() => setRecordatorioId(op.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${
                  recordatorioId === op.id
                    ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                    : "border-[#D1D5DB] bg-white text-[#111827]"
                }`}
              >
                {op.label}
              </button>
            ))}
          </div>
        </section>

        {/* Botones */}
        <div className="flex gap-3">
          <button
            onClick={handleContinuar}
            disabled={!formCompleto || cargando}
            className={`px-6 py-2.5 rounded-lg font-semibold text-sm transition-colors ${
              formCompleto && !cargando
                ? "bg-[#2563EB] text-white hover:bg-[#1D4ED8]"
                : "bg-[#D1D5DB] text-[#9CA3AF] cursor-not-allowed"
            }`}
          >
            {cargando ? "Iniciando..." : "Continuar"}
          </button>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-2.5 rounded-lg font-semibold text-sm border border-[#D1D5DB] text-[#6B7280] hover:bg-[#F3F4F6]"
          >
            Cancelar
          </button>
        </div>
      </main>
    </div>
  );
}