# Capresca — reglas siempre vigentes

El código del sistema nuevo vive en **`capresca-nuevo/`** (FastAPI + Postgres + React/Vite/TS + Docker).
Su guía completa está en `capresca-nuevo/CLAUDE.md` — leerla antes de tocar ese proyecto.

## Antes de CUALQUIER cambio, respetar los dos controles (obligatorio)
Se aplican en cada tarea, no sólo cuando "aparecen" en memoria:

1. **Principios de diseño / UI** → app: *Controles de Versión → Principios de diseño*.
   Lo esencial: tablas con el componente **`DataTable`** (modelo **Maestro de clientes**), idénticas en
   todo el sistema salvo aclaración; layout de ABM header→toolbar→tabla→form; badge **`new`** en
   opciones nuevas; pills de estado; CSS **scopeado por pantalla**; colores por variables de tema;
   confirmar acciones irreversibles.
2. **Principios de arquitectura** → app: *Controles de Versión → Principios de arquitectura*.
   Lo esencial: unicidad concurrente (primer-libre + SAVEPOINT, la DB es árbitro), idempotency-key en
   altas, motor único de cálculo, event-sourcing + recompute, snapshot congelado, contabilidad
   balanceada, cuatro-ojos/N-ojos.
3. **QA profundo**: verificar persistencia real en DB y probar altas contra Postgres (no sólo SQLite);
   cada bug suma su caso en Controles de Versión y su entrada en `salida/hallazgos.md`; limpiar datos
   demo de producción.

Si una decisión aporta un principio nuevo, **sumarlo** a `PRINCIPIOS` / `PRINCIPIOS_DISENO` en
`capresca-nuevo/backend/app/api/controles_version.py`.
