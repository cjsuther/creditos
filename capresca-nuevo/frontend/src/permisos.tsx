import { createContext, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, getToken } from "./api";
import { MENU, items as itemsDe } from "./menu";

// RBAC en el front: gatea menú, rutas y acciones según los permisos efectivos del usuario logueado.
// Regla: `sinRestricciones` (ADMG o perfil sin RBAC configurado) ve/hace todo.
const ORDEN: Record<string, number> = { NINGUNO: 0, CONSULTA: 1, ESCRITURA: 2, TOTAL: 3 };

type Estado = { sinRestricciones: boolean; permisos: Record<string, string>; cargado: boolean };
type Ctx = { estado: Estado; nivel: (r: string) => string; puedeVer: (r: string) => boolean; puedeEscribir: (r: string) => boolean; recargar: () => void };

const PermisosCtx = createContext<Ctx>({
  estado: { sinRestricciones: true, permisos: {}, cargado: false },
  nivel: () => "TOTAL", puedeVer: () => true, puedeEscribir: () => true, recargar: () => {},
});

// Caché por token: evita re-fetch en cada navegación (Layout se remonta por ruta).
let _cache: Estado | null = null;
let _cacheToken = "";

export function PermisosProvider({ children }: { children: React.ReactNode }) {
  const [estado, setEstado] = useState<Estado>(_cache ?? { sinRestricciones: true, permisos: {}, cargado: false });

  function recargar() {
    const tok = getToken() || "";
    if (!tok) { setEstado({ sinRestricciones: true, permisos: {}, cargado: true }); return; }
    if (_cacheToken === tok && _cache) { setEstado(_cache); return; }
    api.misPermisos()
      .then((d: any) => { _cache = { sinRestricciones: d.sinRestricciones, permisos: d.permisos || {}, cargado: true }; _cacheToken = tok; setEstado(_cache); })
      .catch(() => setEstado((e) => ({ ...e, cargado: true })));
  }
  useEffect(() => { recargar(); }, []);

  const nivel = (ruta: string) => estado.sinRestricciones ? "TOTAL" : (estado.permisos[ruta] || "NINGUNO");
  const puedeVer = (ruta: string) => ORDEN[nivel(ruta)] >= 1;
  const puedeEscribir = (ruta: string) => ORDEN[nivel(ruta)] >= 2;
  return <PermisosCtx.Provider value={{ estado, nivel, puedeVer, puedeEscribir, recargar }}>{children}</PermisosCtx.Provider>;
}

export const usePermisos = () => useContext(PermisosCtx);

// Nivel del usuario sobre la PANTALLA actual. `soloLectura` = tiene acceso pero no ESCRITURA
// (para ocultar/deshabilitar botones de alta/edición/baja). No aplica durante la carga.
export function useNivelActual() {
  const { pathname } = useLocation();
  const { nivel, puedeEscribir, estado } = usePermisos();
  const ruta = rutaMenuDe(pathname);
  return {
    ruta,
    nivel: ruta ? nivel(ruta) : "TOTAL",
    soloLectura: !!ruta && estado.cargado && !puedeEscribir(ruta),
  };
}

// Invalida la caché (llamar tras login/logout para releer permisos).
export function invalidarPermisos() { _cache = null; _cacheToken = ""; }

// Ruta del menú que corresponde a un pathname (la más específica que sea prefijo).
export function rutaMenuDe(pathname: string): string | null {
  let mejor: string | null = null;
  for (const m of MENU) for (const i of itemsDe(m)) {
    if (pathname === i.to || pathname.startsWith(i.to + "/")) {
      if (!mejor || i.to.length > mejor.length) mejor = i.to;
    }
  }
  return mejor;
}
