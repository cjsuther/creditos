import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { logout } from "../api";
import Icon from "./Icon";
import Logo from "./Logo";

import { MENU, items } from "../menu";
import { usePermisos } from "../permisos";

const OCULTOS_KEY = "sidebar_mostrar_ocultos";

export default function Sidebar() {
  const location = useLocation();
  const nav = useNavigate();
  const { puedeVer, estado } = usePermisos();
  const esAdmin = estado.sinRestricciones;   // sólo el administrador puede revelar los módulos ocultos
  const [mostrarOcultos, setMostrarOcultos] = useState<boolean>(() => {
    try { return localStorage.getItem(OCULTOS_KEY) === "1"; } catch { return false; }
  });
  const toggleOcultos = () => setMostrarOcultos((v) => {
    const n = !v; try { localStorage.setItem(OCULTOS_KEY, n ? "1" : "0"); } catch { /* ignore */ }
    return n;
  });
  const revelar = esAdmin && mostrarOcultos;   // el admin reveló los módulos/opciones ocultos
  // Un módulo `oculto` sólo se muestra si el admin reveló; en un módulo `soloNuevos` las opciones
  // heredadas (sin `nuevo`) también quedan ocultas hasta revelar.
  const visibles = MENU.filter((m) => !m.oculto || revelar);
  const moduloActivo = visibles.find((m) => items(m).some((i) => location.pathname.startsWith(i.to)));
  const [abierto, setAbierto] = useState<string | null>(moduloActivo?.label ?? "Clientes");

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Logo size={48} onDark />
        <div>
          <span className="sidebar-logo">C.C. y P.P.</span>
          <span className="sidebar-sub">Ca.Pre.S.Ca.</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        {visibles.map((m) => {
          // Grupos con al menos una pantalla visible para el perfil (y, en módulos soloNuevos, sólo las
          // opciones `nuevo` salvo que el admin haya revelado las heredadas).
          const grupos = m.grupos
            .map((g) => ({ ...g, items: g.items.filter((i) => puedeVer(i.to) && (!m.soloNuevos || i.nuevo || revelar)) }))
            .filter((g) => g.items.length > 0);
          if (grupos.length === 0) return null;                 // módulo sin pantallas visibles → oculto
          const expandido = abierto === m.label;
          const activoAqui = grupos.some((g) => g.items.some((i) => location.pathname.startsWith(i.to)));
          return (
            <div key={m.label} className="sb-group">
              <button className={`sb-modulo ${activoAqui ? "activo" : ""}`}
                      onClick={() => setAbierto(expandido ? null : m.label)}>
                <span className="sb-icon"><Icon name={m.icon} /></span>
                <span className="sb-label">{m.label}</span>
                <span className={`sb-chevron ${expandido ? "abierto" : ""}`}><Icon name="chevron" size={14} /></span>
              </button>
              {expandido && (
                <div className="sb-items">
                  {grupos.map((g) => (
                    <div key={g.label} className="sb-sub">
                      {g.items.map((i) => (
                        <NavLink key={i.to} to={i.to}
                          className={({ isActive }) => `sb-item ${isActive ? "activo" : ""}`}>
                          {i.nuevo && <span className="sb-new">new</span>}{i.label}
                        </NavLink>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      {esAdmin && (
        <button className={`sb-ocultos ${mostrarOcultos ? "on" : ""}`} onClick={toggleOcultos}
                title="Módulos ocultos (solo administradores)">
          <Icon name={mostrarOcultos ? "eye" : "eye-off"} size={15} />
          {mostrarOcultos ? "Ocultar módulos" : "Mostrar módulos ocultos"}
        </button>
      )}
      <button className="sb-salir" onClick={() => { logout(); nav("/login"); }}><Icon name="logout" size={16} /> Salir</button>
    </aside>
  );
}
