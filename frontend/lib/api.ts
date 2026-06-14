// frontend/lib/api.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ConfiguracionSincronizacion {
  ciclo: number;
  anio: number;
  campus: boolean;
  paideia: boolean;
}

export interface EstadoSesion {
  sesion_id: string;
  estado: string;
  mensaje: string;
  progreso: number;
  eventos: any[];
  total_campus: number;
  total_paideia: number;
  nombre_calendario?: string;
  calendar_id?: string;
  config?: {
    ciclo: number;
    anio: number;
    campus: boolean;
    paideia: boolean;
  };
  logs?: string[];
  pdfs?: any[];
  insertados?: number;
  total_insertar?: number;
  ultimo_evento?: string;
}

// Inicia una nueva sincronización
export async function iniciarSincronizacion(
  config: ConfiguracionSincronizacion
): Promise<{ sesion_id: string; estado: string; mensaje: string }> {
  const res = await fetch(`${API_URL}/sincronizacion/iniciar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return res.json();
}

// Consulta el estado de una sesión
export async function obtenerEstado(sesionId: string): Promise<EstadoSesion> {
  const res = await fetch(`${API_URL}/sincronizacion/${sesionId}/estado`);
  return res.json();
}

// Obtiene los eventos extraídos
export async function obtenerEventos(sesionId: string) {
  const res = await fetch(`${API_URL}/sincronizacion/${sesionId}/eventos`);
  return res.json();
}

// Verifica que el backend está activo
export async function verificarBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`);
    const data = await res.json();
    return data.estado === "ok";
  } catch {
    return false;
  }
}

export async function confirmarSincronizacion(
  sesionId: string,
  nombreCalendario: string
): Promise<void> {
  await fetch(`${API_URL}/sincronizacion/${sesionId}/confirmar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre_calendario: nombreCalendario }),
  });
}