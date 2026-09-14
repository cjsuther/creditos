"""Controles de Versión — documentación viva del módulo Configurar Créditos.

Introspecciona el esquema real (tablas + columnas + relaciones) y las rutas de la API,
y expone un registro de cambios curado. Así el documento nunca queda desactualizado.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import inspect

from app.core.database import engine
from app.deps import get_current_user

router = APIRouter(prefix="/api/controles-version", tags=["controles-version"],
                   dependencies=[Depends(get_current_user)])

# Agrupación de tablas para el diagrama.
GRUPOS_TABLA = [
    ("Catálogo de producto", ["pp_linea", "pp_grupo", "pp_familia", "pp_producto",
                              "pp_producto_version", "pp_producto_tasa", "pp_producto_cargo",
                              "pp_producto_componente", "pp_componente_definicion", "pp_moneda"]),
    ("Calculador (cronograma)", ["pp_calculador", "pp_calculador_version"]),
    ("Solicitudes", ["pp_solicitud"]),
    ("Contratos y servicing", ["pp_contrato", "pp_cuota_contrato", "pp_actividad"]),
    ("Simulaciones", ["pp_simulacion", "pp_cuota_simulada"]),
    ("Bundles (paquetes)", ["pp_bundle", "pp_bundle_item"]),
    ("Maestros compartidos", ["impuestos", "indices_referencia", "feriados"]),
    ("Contabilidad (integración)", ["asientos", "asientos_lineas"]),
    ("Infraestructura", ["pp_idempotencia"]),
    ("Workflow de aprobaciones", ["pp_workflow_regla", "pp_workflow_nivel", "pp_workflow_nivel_usuario", "pp_workflow_aprobacion", "pp_workflow_pendiente"]),
]

# Registro de cambios del arco Configurar Créditos (curado).
CHANGELOG = [
    ("Fases 1–3", "Product builder + catálogo + persistencia (tablas pp_*)"),
    ("Fase 4", "Workflow de aprobación (borrador→revisión→aprobado→publicado) con cuatro-ojos"),
    ("Fases 5–6", "Oferta/originación (snapshot congelado) y servicing (pago, payoff)"),
    ("Diseño guiado", "Editores por componente, múltiples ítems, inspector de datos, historial/diff"),
    ("Fase A", "Biblioteca de condiciones: Maestro de Impuestos + Índices + tasa variable"),
    ("Fase B", "Reglas de negociación: banda TNA min/max enforzada al originar"),
    ("Fase C", "Propiedades nombradas por componente (INTEREST con lista de propiedades)"),
    ("Fase D", "Herencia de productos/familias (deltas + propagación del padre)"),
    ("Fase E", "Disponibilidad/segmentación (segmentos, canales, edad, vigencia)"),
    ("Fase F", "Servicing event-sourced: backdating y reversa de actividades"),
    ("Fase G", "Periodic rules (repricing) + bundles + relationship pricing"),
    ("Integración contable", "Asientos automáticos de originación/servicing al Libro Diario"),
    ("Solicitudes legacy", "Originar desde una solicitud de crédito aprobada real (VFP)"),
    ("Simulaciones persistidas", "Guardar escenarios del simulador con su cronograma"),
    ("Prueba en vivo flotante", "Panel reactivo a toda la config con detección de impacto"),
    ("Tablero de cartera", "Totales, saldos, cobranza, mora y desglose por línea"),
    ("Cronograma unificado", "Única fuente de verdad backend: preview == contrato originado"),
    ("Wizard de originación", "Cliente → Simular → Datos → Otorgar → Liquidación/Desembolso"),
    ("Exportación", "Contrato a PDF y cartera a Excel"),
    ("Devengamiento", "Asiento de devengo de interés (sin duplicar el ingreso)"),
    ("Tasas visibles", "TNA/TEA/CFT calculadas en vivo en el encabezado del configurador (la TNA se persiste)"),
    ("Vigencia por versión", "Cada versión tiene vigencia desde/hasta; la efectiva se resuelve por fecha "
                             "(oferta/originación/herencia usan la versión vigente hoy). Al publicar v2 se cierra "
                             "la vigencia de la anterior — tracking de créditos otorgados sobre versiones previas"),
    ("Sistema de cálculos", "Pantalla de transparencia: fórmula por sistema, motor certificado por checksum "
                            "y depurador paso a paso del armado de cada cuota"),
    ("Piso de banda duro", "Relationship pricing no perfora el piso de la banda de negociación (ni al originar "
                           "ni en el repricing de tasa variable)"),
    ("Vencimientos en feriado", "El ajuste de días hábiles saltea feriados nacionales fijos; los movibles se "
                                "inyectan por parámetro. Gobernanza del calculador (pp_calculador_version) visible"),
    ("Maestro de feriados", "Calendario por país (Contabilidad → Feriados): ABM manual + import de fuente oficial "
                            "(Nager.Date) con respaldo calculado; alimenta el ajuste a día hábil del motor"),
    ("Regresión ampliada", "Casos de los bugs recientes registrados aquí (vigencia, piso de banda, sistema de "
                           "cálculos, feriados) y badge 'new' en las opciones creadas en la migración"),
    ("Fix doble cobro", "El cargo al desembolso se cobraba en la 1ª cuota Y se restaba del neto (doble). "
                        "Ahora el cliente recibe el monto completo; el cargo vive sólo en el cronograma"),
    ("Fix financiable", "'Financiable' ya no se ignora cuando el momento es PRORRATEADO: tiene prioridad y "
                        "el cargo se suma al capital"),
    ("Mora aplicada", "El componente OVERDUE (moraTNA) ahora se aplica de verdad: al pagar una cuota vencida "
                      "se cobra el interés punitorio (con IVA y días de gracia) y se asienta a 4.1.02"),
    ("Solicitudes de crédito", "Nueva opción: alta de solicitudes (cliente registrado o alta express), workflow "
                               "con cuatro-ojos y elegibilidad; una solicitud APROBADA se origina como contrato "
                               "(pp_solicitud, /api/solicitudes)"),
    ("Situaciones de pago", "Pago parcial de cuota, prepago de capital (baja cuota/plazo), diferimiento (capitaliza "
                            "interés) y refinanciación (nueva tasa+plazo) — event-sourced, con reversa idempotente"),
    ("Caja de créditos", "Nueva opción: cobranza dedicada de contratos con medio de pago, recibo y asiento al "
                         "Libro Diario (orquesta el servicing, no recalcula)"),
    ("Situación del cliente", "Nueva opción: consulta consolidada por cliente (busca por nombre) con sus contratos "
                              "de línea nueva, saldos, próxima cuota, mora al día y detalle expandible (plan + actividad); "
                              "resumen con capital colocado y saldo vigente"),
    ("Simulación de refinanciación", "La refinanciación abre un panel flotante que previsualiza el préstamo nuevo "
                                     "(nueva cuota, capital + interés total, TEA, CFT y plan completo) usando el mismo motor "
                                     "antes de confirmar; se agregó un refresh a la cartera de contratos originados"),
    ("Reorganización de pantallas", "Originar Crédito quedó SÓLO con el wizard de originación. El tablero pasó a la nueva "
                                    "'Tablero de cartera' (analítica por estado/sistema/línea/rango de saldo) y la lista de "
                                    "contratos + el detalle/servicing completo se movieron a 'Situación del cliente' (sin duplicar)"),
]

# ---------------- casos de prueba por pantalla ----------------
# tipo: "auto" = cubierto por la suite pytest · "live" = corrible en vivo (read-only) desde acá.
CASOS = [
    # Configurar Créditos
    ("cfg-catalogo", "Configurar Créditos", "Catálogo sembrado y permisos por perfil", "auto", "test_catalogo_sembrado_y_permisos / test_permisos_por_perfil"),
    ("cfg-workflow", "Configurar Créditos", "Workflow de aprobación con cuatro-ojos", "auto", "test_workflow_completo_cuatro_ojos"),
    ("cfg-herencia", "Configurar Créditos", "Herencia de productos (deltas + propagación)", "auto", "test_herencia_deriva_de_padre"),
    ("cfg-herencia-vig", "Configurar Créditos", "El hijo hereda la versión VIGENTE del padre, no una v2 con vigencia futura", "auto", "test_herencia_usa_version_vigente_no_futura_del_padre"),
    ("cfg-multiples", "Configurar Créditos", "Múltiples ítems de cargos/impuestos", "auto", "test_multiples_items_cargos_impuestos"),
    ("cfg-sim", "Configurar Créditos", "Simulaciones persistidas (guardar/listar/borrar)", "auto", "test_simulaciones_persistidas"),
    ("cfg-vigencia", "Configurar Créditos", "Vigencia por versión: v2 a futuro no reemplaza a v1 hoy", "auto", "test_version_vigencia_efectiva_a_futuro"),
    ("cfg-codigo-unico", "Configurar Créditos", "Crear línea ('Crear y diseñar') no colisiona el código LP-NUEVA-NN aunque ya existan líneas nuevas (H-097: antes daba Error 500 por clave única)", "auto", "test_crear_linea_no_colisiona_codigo"),
    ("cfg-valida-guardar", "Configurar Créditos", "Guardar config rechaza contradicciones/negativos con 422 (min>max, TNA negativa, plazo min>max); antes se persistía cualquier disparate (H-099)", "auto", "test_guardar_config_rechaza_invalidos"),
    ("cfg-borrar-ref", "Configurar Créditos", "Borrar una línea referenciada (padre de otra / con contratos) devuelve 409 claro, no 500 crudo por FK (H-099)", "auto", "test_borrar_linea_con_referencias_da_409"),
    ("ori-numero-unico", "Originar Crédito", "El numero_contrato (CTO-AAAA-NNNNN, único) no colisiona al borrarse un contrato — hermano de H-097, se usa el primer número libre", "auto", "test_originar_no_colisiona_numero_contrato"),
    ("sol-numero-unico", "Solicitudes", "El numero de solicitud (SOL-AAAA-NNNNN, único) no colisiona al borrarse una solicitud — hermano de H-097", "auto", "test_solicitud_no_colisiona_numero"),
    ("num-concurrencia", "Configurar Créditos", "Numeración segura ante concurrencia multi-usuario: si dos requests toman el mismo 'primer libre', la constraint única es el árbitro y se REINTENTA con un número fresco (SAVEPOINT); no explota con 500", "auto", "test_numbering_reintenta_ante_colision_concurrente"),
    ("idem-key", "Configurar Créditos", "Idempotency-Key: dos altas con la misma clave devuelven el mismo resultado y crean UN registro; el pago no se duplica en un reintento (línea, solicitud, originar, refinanciar, servicing)", "auto", "test_idempotency_key_no_duplica_altas"),
    ("arq-principios", "Principios de arquitectura", "El catálogo de principios de arquitectura está disponible (incluye 'unicidad concurrente', 'trazabilidad temporal' e 'idempotency-key') con título, enunciado y motivo", "live", ""),
    ("dis-principios", "Principios de diseño", "El catálogo de principios de diseño está disponible (incluye 'tabla única = DataTable / modelo Maestro de clientes') con título, enunciado y ejemplo", "live", ""),
    ("dis-candado", "Principios de diseño", "Candado mecánico (frontend/scripts/check-diseno.mjs + hook PostToolUse) de TRES principios: 'tabla única' (nada de <table> cruda sin DataTable), 'color por tema' (nada de hex cromático fijo; #fff/#000 permitidos) y 'CSS scopeado por pantalla' (nada de clases genéricas bare tipo .card/.row en el <style> de una página; deben ir prefijadas — bug H-083). Escapes: comentario 'diseño-ok' o allowlists diseno-allow-tablas/colores/clases.txt", "manual", ""),
    ("inbox-cuatro-ojos", "Inbox de aprobaciones", "El inbox lista las tareas pendientes de aprobación con quién las pidió y NO muestra las que el propio usuario envió (cuatro-ojos)", "auto", "test_inbox_aprobaciones_cuatro_ojos"),
    ("wf-configurable", "Workflow de aprobaciones", "El motor de workflow (Seguridad) cambia quién aprueba: un override INCLUIR habilita a un usuario sin el rol; sólo un ADMG configura", "auto", "test_workflow_config_cambia_quien_aprueba"),
    ("wf-cadena", "Workflow de aprobaciones", "Cadena de N niveles en serie: con 2 niveles, la 1ª aprobación NO cierra (sigue EN_REVISION) y recién la 2ª (otro rol/usuario) pasa a APROBADO", "auto", "test_workflow_cadena_n_niveles"),
    ("wf-concurrencia", "Workflow de aprobaciones", "Un nivel de la cadena se aprueba UNA sola vez: constraint única (objeto, objeto_id, nivel_orden) evita que dos aprobadores concurrentes del mismo nivel completen la cadena sin aprobar los niveles superiores (bypass de N-ojos). aprobar_paso traduce la carrera a 409, no 500", "auto", "test_un_nivel_se_aprueba_una_sola_vez"),
    ("caja-recibo-unico", "Aplicativo de caja", "El Nº de recibo de cobranza es único (constraint DB uq_recibos_numero): dos cajeros concurrentes no pueden emitir el mismo número (TOCTOU de max+1). La emisión usa crear_con_numero_unico (primer-libre + SAVEPOINT + reintento). H-108", "auto", "test_recibo_numero_unico"),
    ("op-numero-unico", "Órdenes de pago", "El Nº de orden de pago es único (uq_ordenes_pago_numero): la DB frena la carrera de dos procesos con el mismo número. Creación vía crear_con_numero_unico. H-108", "auto", "test_orden_pago_numero_unico"),
    ("agencia-recibo-unico", "Aplicativo de caja (quiniela)", "El Nº de recibo de cobranza de agencia es único (uq_caja_pagos_agencia_no_recibo): la DB es árbitro contra el TOCTOU de max+1. H-108", "auto", "test_recibo_agencia_no_recibo_unico"),
    ("num-compuesto-unico", "Despacho / Seguros / Mesa / Configurar Créditos", "Nºs con alcance compuesto únicos por la DB: Resolución (anio,tipo,numero), Póliza (global), Turno de mesa (fecha,numero), PPVersion (producto_id,numero_version). Data VFP verificada sin duplicados antes de la constraint. H-108", "auto", "test_resolucion_numero_unico_por_anio_tipo"),
    ("idem-transiciones", "Créditos / Contratos", "Idempotency-Key en transiciones que crean/mueven dinero: alta de solicitud, otorgar, desembolsar, devengar. Un reintento/doble-click no duplica la operación (con_idempotencia). H-108", "auto", "test_alta_solicitud_idempotente"),
    ("contab-balance-guarda", "Contabilidad", "Guarda mecánica del principio 'contabilidad balanceada': un evento before_insert rechaza cualquier asiento de la app (doble partida) con Σdebe≠Σhaber; los migrados del mayor plano de VFP (origen='legacy', una pierna) se excluyen. H-109", "auto", "test_asiento_app_desbalanceado_falla"),
    ("reversa-idempotente", "Situación del cliente / servicing", "Event-sourcing: una actividad se reversa UNA sola vez (constraint única uq_pp_actividad_reversa_de) — la DB frena dos reversar concurrentes (doble contra-asiento). El endpoint traduce la carrera a 409. H-110", "auto", "test_reversa_de_unico"),
    ("recompute-determinista", "Situación del cliente / servicing", "Event-sourcing: _recompute es determinista/idempotente — resetea al cronograma pristino del snapshot y re-aplica las actividades no-reversadas; recomputar N veces da el mismo estado. H-110", "auto", "test_recompute_determinista"),
    ("equiv-tipo-calculo", "Sistema de cálculos", "Equivalencia vs VFP: el mapeo tipo_calculo estaba mal (VFP 1=Directo, 2/3=Francés; la app lo enrutaba distinto). Fix: el migrador traduce VFP→app {1:3, 2:1, 3:1} (opción B). El motor reproduce al centavo los créditos reales migrados (Francés y Directo) usando el tipo_calculo corregido de la línea. H-111", "auto", "test_equivalencia_por_tipo_calculo"),
    ("seg-jwt-secret", "Seguridad", "La app no arranca en producción con el JWT_SECRET default del código (público → forjable): un model_validator lo exige por entorno fuera de development/test. Revisión de seguridad: mutaciones con auth, password_hash no expuesto, SQL dinámica sólo sobre registro fijo. H-112", "auto", "test_produccion_rechaza_secreto_default"),
    ("perf-balance-join", "Balance / Mayor", "Performance: el balance de sumas y saldos hacía join a asientos siempre; se hizo condicional al filtro de fecha (1.0s→0.14s sobre 2M líneas). La DB está bien indexada; sin índices faltantes urgentes. H-113", "manual", ""),
    ("wf-gate-desembolso", "Workflow de aprobaciones", "Gate de DESEMBOLSO/REFINANCIACION: con la regla activa, la acción queda PENDIENTE (aparece en el Inbox del aprobador, no del emisor); al aprobar se ejecuta la operación real", "auto", "test_gate_desembolso_pendiente_y_aprobacion"),
    ("abm-usuarios", "Usuarios", "ABM completo: editar (nombre+perfil), baja y reactivar; búsqueda y datalist de perfiles en uso", "auto", "test_abm_usuario_editar_baja_reactivar"),
    ("abm-perfiles", "Perfiles", "ABM de perfiles (maeperfil): alta/editar/habilitar; no se borra un perfil en uso (409) y el maestro reporta cuántos usuarios lo tienen", "auto", "test_abm_perfiles_crud"),
    ("perfil-permisos", "Perfiles", "Permisos por pantalla (RBAC): nivel Sin acceso/Consulta/Escritura/Total por ruta del menú, set individual y bulk por módulo; NINGUNO borra la fila", "auto", "test_perfil_permisos_por_pantalla"),
    ("perfil-usuarios", "Perfiles", "Asignar usuarios a un perfil desde el maestro (les setea el perfil) y listarlos como miembros", "auto", "test_perfil_asignar_usuarios"),
    ("perfil-enforce", "Perfiles", "Enforcement RBAC: perfil sin permisos = sin restricciones (legacy); al configurar una pantalla se enforca; el endpoint guardado da 403 sin permiso y 200 con CONSULTA; ADMG siempre. El menú y las rutas del front se recortan según los permisos", "auto", "test_enforcement_permiso_por_pantalla"),
    ("qa-usuarios-validacion", "Usuarios", "QA de alta/baja: rechaza password vacío/corto (<6), username vacío y reset vacío (422); no permite auto-baja ni dar de baja al último admin (409); baja impide login y reactivar lo restaura", "auto", "test_qa_alta_usuario_password_vacio_rechazado"),
    ("qa-perfiles-validacion", "Perfiles", "QA de perfiles: rechaza código >6 (422); borrar cascadea permisos; un perfil DESHABILITADO bloquea el login de sus usuarios (403); ruta de permiso malformada rechazada (422)", "auto", "test_qa_perfil_deshabilitado_bloquea_a_sus_usuarios"),
    ("iam-cadena", "Usuarios", "IAM: el usuario hereda permisos por la cadena Usuario→Grupo→Rol→Permiso; multi-rol; acceso efectivo = unión con nivel máximo", "auto", "test_iam_cadena_grupo_rol_permiso"),
    ("iam-vigencia", "Usuarios", "IAM: las asignaciones del usuario (grupo/rol) tienen vigencia desde/hasta; una asignación vencida deja de otorgar acceso (cobertura de licencia que se apaga sola)", "auto", "test_iam_vigencia_vence_el_acceso"),
    ("iam-grupos-ui", "Grupos", "Pantalla de Grupos (ABM + asignar roles) y editor de Usuario con grupos/vigencia y vista de 'acceso efectivo'; 'Perfiles' renombrado a 'Roles'", "manual", ""),
    ("iam-permiso-directo", "Usuarios", "IAM: permiso directo sobre una pantalla (además de roles/grupos), con vigencia opcional; nivel NINGUNO lo borra; ruta inválida = 422; se une al acceso efectivo", "auto", "test_iam_permiso_directo_vigencia"),
    ("iam-usuario-editor-tabs", "Usuarios", "Editor de acceso del usuario en pestañas: Roles (★ principal) · Grupos (con vigencia) · Permisos directos · Acceso efectivo (unión hoy) · Datos; picker de pantallas deduplicado; terminología unificada a 'rol'", "manual", ""),
    ("iam-asignar-rol-aditivo", "Roles (perfiles)", "Sumar un rol a usuarios desde la pantalla de Roles es ADITIVO: lo agrega como rol adicional sin pisar el principal; miembros = unión (principal + adicional) con flag; idempotente; borrar rol bloqueado si es principal/adicional de alguien o está en un grupo", "auto", "test_iam_asignar_rol_es_aditivo"),
    ("iam-rol-codigo-unico", "Roles (perfiles)", "El código de rol es único: chequeo app + constraint DB como árbitro (uq_perfiles_codigo); las altas de rol/grupo/usuario traducen la violación de unicidad concurrente a 409, no 500", "auto", "test_iam_rol_codigo_unico"),
    ("wf-reglas", "Workflow de aprobaciones", "Las 4 reglas (LINEA/SOLICITUD activas, DESEMBOLSO/REFINANCIACION inactivas) se siembran con 1 nivel rol ADMG cuatro-ojos", "live", ""),
    ("no-reversar-refinanciacion", "Servicing / Contratos", "H-154 (QA): reversar la actividad RENEGOTIATION del contrato original está bloqueado (422). Reactivaría el viejo (recompute → ACTIVO con el saldo entero) mientras el nuevo sigue vivo con su desembolso → el mismo capital colocado dos veces. El front oculta el botón ↩ sobre RENEGOTIATION.", "auto", "test_no_reversar_refinanciacion_evita_doble_capital"),
    ("liquidar-lote-idempotente", "Liquidación por lote", "H-154 (QA): liquidar un lote es idempotente (Idempotency-Key) y serializado — cada contrato se toma con with_for_update + recheck de estado A_LIQUIDAR dentro de la transacción, así un doble-clic o dos lotes concurrentes NO desembolsan dos veces ni duplican el asiento (el 2º lo ve ya ACTIVO y lo saltea).", "manual", ""),
    ("cobro-caja-idempotente", "Caja", "H-154 (QA): /api/caja/cobrar y /cola/cobrar pasan por con_idempotencia (dinero): un doble-POST con la misma Idempotency-Key no genera dos recibos. El front ya mandaba la clave (postIdem); faltaba honrarla en el backend.", "manual", ""),
    ("idempotencia-pagos-cobros", "Tesorería / Juegos / Créditos", "H-157 (QA): se completó la idempotencia en el resto de los movimientos de dinero — egresos /ordenes/{id}/pagar y /pagar-chequera, juegos /liquidaciones/{id}/cobrar y /agencias/cobrar, y payoff legacy /creditos/{id}/cancelar — todos por con_idempotencia. Un doble-POST con la misma Idempotency-Key devuelve el mismo resultado, no duplica pago/recibo. El front manda la clave (postIdem).", "auto", "test_pagar_op_idempotente / test_cobrar_liquidacion_idempotente"),
    ("oidc-state-one-time", "Portal / Seguridad", "H-158 (QA): el state OIDC de Mi Catamarca es de un solo uso (anti-replay). El nonce firmado se reserva al emitir el login y se CONSUME en el callback; un segundo callback con el mismo state (replay dentro de la ventana de validez) se rechaza (400). Antes el state firmado evitaba CSRF pero podía reusarse hasta expirar.", "auto", "test_state_no_reutilizable"),
    ("dbf-memo-fpt-fix", "Migradores / ETL", "H-165: el lector de DBF resolvía mal el archivo de memos (.fpt): recortaba 1 carácter del path ('archivo.dbf' → buscaba 'archivo.dbfpt') y nunca lo encontraba, así que TODOS los campos memo (M) migraban vacíos. Se resuelve por nombre base (splitext + .fpt/.FPT/.dbt). Además, los memos vienen en RTF: se agregó `etl/rtf.rtf_a_texto` (algoritmo striprtf) para migrarlos a texto plano. Impacto: los textos de las resoluciones (41.300/41.396) y las plantillas de los modelos (336/338) ahora tienen contenido; beneficia a cualquier migrador con memos.", "manual", ""),
    ("despacho-resolucion-legacy", "Despacho", "H-164: la pantalla de Resolución/Disposición replica la del VFP legacy — N° Correlativo (se asigna al grabar) y N° Real (se carga aparte, secuencial por tipo+año), Modelo a utilizar (su descripción ES el motivo; su plantilla es el texto base), Importe, Exp./Nota origen, Texto del instrumento legal y grilla de Beneficiarios. Se migraron los DBF reales: 338 modelos (rtf), 41.396 resoluciones y 127.875 beneficiarios (Despacho/*.dbf) al modelo actual (Resolucion + ResolucionBeneficiario + plantilla en ModeloResolucion). Migrador re-ejecutable desde Seguridad → Migradores (clave 'despacho').", "auto", "test_resolucion_modelo_beneficiarios_y_numero_real"),
    ("portal-identidad-declarada", "Portal ciudadano", "H-162: Mi Catamarca sólo confirma que la persona existe (no devuelve su perfil), así que el ciudadano DECLARA su identidad en \"Tus datos\": apellido, nombre y DNI (obligatorios, DNI 7-8 díg.) — se sacó el botón \"Traer mis datos de Mi Catamarca\" (haberes). El backend exige y normaliza esos datos (422 si faltan) y arma cliente_datos.apellido_nombre = \"Apellido, Nombre\". Los documentos (DNI/recibo) se adjuntan en el mismo paso de datos y se suben al enviar.", "auto", "test_enviar_exige_identidad_declarada"),
    ("portal-docs-ui", "Portal ciudadano", "H-160/H-163: el ciudadano adjunta su documentación (DNI frente/dorso, recibo de sueldo, otro) en el paso \"Tus datos\" de la solicitud (selección en el cliente; se suben al enviar). Muestra la lista con tipo/nombre/tamaño e ícono IMG/PDF, con quitar; validación JPG/PNG/PDF, máx 5 MB, hasta 10. La sección de documentos NO está en \"Mis solicitudes\" (post-envío): el pedido de docs es sólo al cargar la solicitud (consistente con H-131). El backend de documentos sigue completo y probado.", "auto", "test_documento_subir_listar_descargar / test_documento_valida_formato_y_owner"),
    ("icono-notificaciones-moderno", "UX", "H-161: se modernizó el ícono de notificaciones — bell redondeado estilo Lucide nuevo en el backoffice (Icon.tsx) y SVG equivalente en el portal (reemplaza el emoji 🔔); badge como pill con anillo del fondo y pulso sutil (respeta prefers-reduced-motion), micro-rotación al hover.", "manual", ""),
    ("portal-token-expira-expulsa", "Portal / Seguridad", "H-159 (QA): si el token del portal vence a mitad de sesión, cualquier 401 limpia el token y emite un evento global que devuelve al ciudadano a la pantalla de ingreso (sin dejar la UI rota hasta recargar). Antes el estado de sesión sólo se evaluaba al montar la app.", "manual", ""),
    ("cliente-cuil-unico", "Clientes", "H-154 (QA): el CUIL del cliente es único con constraint en la DB (uq_clientes_cuil) — dos altas concurrentes con el mismo CUIL no crean duplicado (la 2ª cae en IntegrityError → 409, no check-then-insert). Alta con Idempotency-Key (reintento no duplica) y DV de CUIL validado (422).", "auto", "test_alta_cliente_cuil_unico_y_dv / test_alta_cliente_idempotente"),
    ("iam-auditoria", "Seguridad / IAM", "H-155 (QA): todas las mutaciones de Seguridad (alta/edición/baja/reactivación/clave de usuario, roles principal/adicionales, alta/edición/baja de grupos y sus roles, membresías, permisos directos, ABM de roles y sus permisos por pantalla) dejan rastro en auditoría con quién, operación, antes/después e IP. Antes sólo se auditaba el LOGIN.", "auto", "test_iam_mutaciones_dejan_auditoria"),
    ("rbac-fino-backend", "Seguridad / RBAC", "H-156: el nivel por pantalla que configura Roles se enforca en el BACKEND, no sólo en el front. Las escrituras del Maestro de clientes (alta/edición/baja/reactivación) y del calendario de Feriados exigen nivel ESCRITURA sobre su ruta; un rol con sólo CONSULTA recibe 403. ADMG y los roles sin RBAC configurado siguen pasando (sin_restricciones → TOTAL).", "auto", "test_escritura_cliente_exige_permiso_backend"),
    ("no-degradar-ultimo-admin", "Seguridad / IAM", "H-154 (QA): no se puede dejar el sistema sin administrador por vías distintas a la baja: editar_usuario y set-perfiles no degradan el perfil principal del último ADMG activo (409) y no se puede deshabilitar el rol ADMG (409, si no bloquearía el login de todos).", "auto", "test_qa_no_degradar_ultimo_admin"),
    ("aprobar-exige-rol-wf-inactivo", "Workflow de aprobaciones", "H-153 (QA profundo): resolver una solicitud o aprobar una línea exige rol aprobador AUN con el workflow sembrado INACTIVO (app single-admin). Antes el motor auto-aprobaba sin mirar permisos → cualquier usuario autenticado resolvía. Ahora, sin workflow activo, gatea _req_aprueba (rol aprobador de la pantalla); con workflow activo gatea el motor por rol de nivel (permite niveles intermedios con roles no-aprobadores) + cuatro-ojos", "auto", "test_aprobar_exige_rol_aun_con_workflow_inactivo / test_aprobar_linea_exige_rol_aun_con_workflow_inactivo"),
    ("grupo-inactivo-corta-acceso", "Seguridad / IAM", "H-153 (QA profundo): desactivar un grupo (activo=False) corta el acceso heredado de TODOS sus miembros de una, sin quitar membresías. Antes roles_de ignoraba Grupo.activo y el grupo seguía otorgando sus roles (y la capacidad de aprobar). Ahora roles_de sólo toma roles de grupos activos", "auto", "test_grupo_inactivo_no_otorga_acceso"),
    ("cuatro-ojos-por-roles", "Workflow de aprobaciones", "H-150: quién aprueba se define con ROLES y GRUPOS, no con overrides por nivel. 'creditos' (XCR) no puede aprobar una línea cuyo nivel exige rol ADMG (403); tras sumarlo a un grupo que otorga ese rol, hereda la capacidad y sí puede. Misma fuente (roles_de) que gobierna las capacidades de las pantallas (caps_creditos)", "auto", "test_workflow_quien_aprueba_via_roles_grupos"),
    # Solicitudes de crédito (línea nueva)
    ("sol-crear", "Solicitudes", "Alta registrada calcula elegibilidad + cuota estimada", "auto", "test_crear_registrado_calcula_evaluacion"),
    ("sol-express", "Solicitudes", "Alta express exige datos mínimos (nombre + CUIL)", "auto", "test_alta_express_requiere_datos_minimos"),
    ("sol-cuatro-ojos", "Solicitudes", "Workflow con cuatro-ojos (quien envía no aprueba)", "auto", "test_workflow_cuatro_ojos / test_cuatro_ojos_bloquea_autoaprobacion"),
    ("sol-no-elegible", "Solicitudes", "No se aprueba una solicitud no elegible (422)", "auto", "test_no_aprobar_solicitud_no_elegible"),
    ("sol-originar", "Solicitudes", "Originar desde APROBADA marca ORIGINADA + liga el contrato (no re-origina)", "auto", "test_originar_desde_solicitud_aprobada"),
    ("sol-promover", "Solicitudes", "Alta express se promueve al maestro de clientes", "auto", "test_promover_cliente_express_al_maestro"),
    # Cálculo de cuotas — opciones de préstamo (todas vía /productos/preview, read-only)
    ("calc-cierra", "Cálculo de cuotas (opciones)", "El cronograma cierra el saldo en 0 y Σcapital = monto", "live", ""),
    ("calc-frances", "Cálculo de cuotas (opciones)", "Sistema francés: cuota constante", "live", ""),
    ("calc-aleman", "Cálculo de cuotas (opciones)", "Sistema alemán: capital constante, interés decreciente", "live", ""),
    ("calc-americano", "Cálculo de cuotas (opciones)", "Sistema americano: capital sólo al final, interés constante", "live", ""),
    ("calc-bullet", "Cálculo de cuotas (opciones)", "Sistema bullet: pago único al vencimiento", "live", ""),
    ("calc-gracia", "Cálculo de cuotas (opciones)", "Período de gracia: primeras cuotas de sólo interés", "live", ""),
    ("calc-trimestral", "Cálculo de cuotas (opciones)", "Frecuencia trimestral: vencimientos cada 3 meses", "live", ""),
    ("calc-adelantada", "Cálculo de cuotas (opciones)", "Cuota adelantada: 1ª cuota sin interés (anticipada)", "live", ""),
    ("calc-cargo-desemb", "Cálculo de cuotas (opciones)", "Cargo al desembolso: cae en la 1ª cuota", "live", ""),
    ("calc-cargo-prorr", "Cálculo de cuotas (opciones)", "Cargo prorrateado: igual en todas las cuotas", "live", ""),
    ("calc-financiable", "Cálculo de cuotas (opciones)", "Cargo financiable: se suma al capital y amortiza", "live", ""),
    ("calc-financiable-prio", "Cálculo de cuotas (opciones)", "'Financiable' tiene prioridad sobre PRORRATEADO (no se ignora)", "auto", "test_financiable_tiene_prioridad_sobre_prorrateado"),
    ("calc-iva-interes", "Cálculo de cuotas (opciones)", "IVA sobre interés sube el costo total", "live", ""),
    ("calc-iva-cargos", "Cálculo de cuotas (opciones)", "IVA sobre cargos sube el costo total", "live", ""),
    ("calc-ajuste-finde", "Cálculo de cuotas (opciones)", "Ajuste de fin de semana: ningún vencimiento cae sábado/domingo", "live", ""),
    ("calc-dia-pago", "Cálculo de cuotas (opciones)", "Día de pago cambia las fechas de vencimiento", "live", ""),
    ("calc-feriado", "Cálculo de cuotas (opciones)", "Ajuste hábil saltea feriados nacionales (no sólo fines de semana)", "live", ""),
    # Sistema de cálculos (transparencia del motor)
    ("sc-catalogo", "Sistema de cálculos", "Motor certificado (checksum) + fórmulas de los 4 sistemas", "live", ""),
    ("sc-debug", "Sistema de cálculos", "Depurador arma las cuotas (interés=saldo·i) y cierra el saldo en 0", "live", ""),
    # Originar Crédito
    ("ori-oferta", "Originar Crédito", "La oferta muestra sólo líneas PUBLICADAS", "live", ""),
    ("ori-segmento", "Originar Crédito", "Segmentación: JUBILADO ve Jubilados y no Personal", "live", ""),
    ("ori-segmento-ap", "Originar Crédito", "Segmentación: AGENTE_PUBLICO ve Personal y no Jubilados", "live", ""),
    ("ori-canal", "Originar Crédito", "Canal CONVENIO: Jubilados sí, Personal no", "live", ""),
    ("ori-edad", "Originar Crédito", "Edad 30: Jubilados (mín. 60) no elegible", "live", ""),
    ("ori-variable", "Originar Crédito", "Existe una línea de tasa VARIABLE (BADLAR)", "live", ""),
    ("ori-bundle", "Originar Crédito", "Existe el bundle BND-CAP-01 con sus miembros", "live", ""),
    ("ori-bundle-vig", "Originar Crédito", "El bundle muestra la versión VIGENTE del miembro, no un borrador/v2 futura", "auto", "test_bundle_muestra_version_vigente_no_borrador"),
    ("ori-tablero", "Originar Crédito", "Tablero de cartera consistente (saldo ≤ capital colocado)", "live", ""),
    ("ori-relacion", "Originar Crédito", "Relationship pricing PREMIUM baja la TNA", "auto", "test_relationship_pricing_descuenta_tna"),
    ("ori-piso", "Originar Crédito", "Relationship pricing no perfora el piso de la banda de negociación", "auto", "test_relationship_pricing_no_perfora_piso_de_banda"),
    ("ori-coherencia", "Originar Crédito", "Preview == contrato originado (cuota/capital/interés/fecha)", "auto", "test_preview_coincide_con_contrato_originado"),
    ("ori-pasos", "Originar Crédito", "Otorgar (A_LIQUIDAR) → desembolsar (ACTIVO)", "auto", "test_otorgar_y_desembolsar_por_pasos"),
    ("ori-doble-cargo", "Originar Crédito", "El cargo al desembolso no se cobra doble (cuota + neto) — neto = monto", "auto", "test_cargo_desembolso_no_se_cobra_doble"),
    ("ori-pago-parcial", "Originar Crédito", "Pago parcial de cuota: acumula en pagado, no baja saldo hasta completar; asiento proporcional", "auto", "test_pago_parcial_de_cuota"),
    ("ori-reversa-parcial", "Originar Crédito", "Reversar un abono parcial restaura pagado (event-sourcing)", "auto", "test_reversa_de_pago_parcial"),
    ("ori-prepago-cuota", "Originar Crédito", "Prepago BAJA_CUOTA: mismo plazo, cuota menor; regenera el tramo", "auto", "test_prepago_baja_cuota"),
    ("ori-prepago-plazo", "Originar Crédito", "Prepago BAJA_PLAZO: menos cuotas; saldo baja por el importe", "auto", "test_prepago_baja_plazo"),
    ("ori-prepago-reversa", "Originar Crédito", "Reversar un prepago restaura el cronograma pristino (idempotencia)", "auto", "test_reversa_de_prepago_restaura_cronograma"),
    ("ori-prepago-parcial", "Originar Crédito", "Un prepago no pierde el pago parcial previo de una cuota (H-096)", "auto", "test_prepago_no_pierde_pago_parcial_previo"),
    ("ori-diferir", "Originar Crédito", "Diferimiento: N cuotas en $0, capitaliza interés, reversa restaura", "auto", "test_diferimiento_capitaliza_interes"),
    ("ori-refinanciar", "Originar Crédito", "Refinanciación: nueva tasa+plazo sobre el saldo; viejo REFINANCIADO", "auto", "test_refinanciacion_cierra_viejo_y_crea_nuevo"),
    ("ori-refi-sim", "Originar Crédito", "Panel flotante de simulación de refinanciación: previsualiza nueva cuota, capital+interés total y CFT antes de confirmar; el preview usa el mismo motor que la refinanciación (coincide con el contrato nuevo)", "manual", ""),
    # Situación del cliente (consulta consolidada línea nueva)
    ("sit-consolidada", "Situación del cliente", "Consulta por cliente: contratos línea nueva con saldo, cuotas pagadas/pendientes, próxima cuota y mora al día; resumen (saldo vigente ≤ capital colocado)", "live", ""),
    ("sit-mora-aldia", "Situación del cliente", "La mora al día se calcula sólo sobre contratos ACTIVOS con cuota vencida", "live", ""),
    ("sit-refleja-db", "Situación del cliente", "El endpoint refleja exactamente lo persistido: filtro por nombre, saldo/estado/cuotas por contrato y resumen == agregación real de la DB", "auto", "test_situacion_cliente_refleja_la_db"),
    ("sit-servicing", "Situación del cliente", "Al expandir un contrato se ve el detalle completo + servicing (pagar/parcial/prepago/diferir/refinanciar/payoff/reversa, plan de cuotas, actividades, asientos); tras cada acción se refresca la fila y el resumen", "manual", ""),
    ("orig-solo-wizard", "Originar Crédito", "Originar quedó SÓLO con el wizard (cliente→simular→datos→otorgar→desembolso); ya no muestra tablero ni lista de contratos ni servicing (migrados). 'Ver contrato' lleva a Situación del cliente", "manual", ""),
    ("tablero-cartera", "Tablero de cartera", "Nueva pantalla analítica: KPIs de cartera + selector 'Analizar por' (Estado/Sistema/Línea/Rango de saldo) con contratos, capital, saldo y barra de participación; export a Excel", "manual", ""),
    ("resumen-cobros", "Resumen de cobros", "Nueva pantalla (VFP frm330150000rptcobcre): cobranza de créditos por período mensual desde las cuotas pagadas (capital/interés/IVA/seguro/gastos + mora residual = total − conceptos); KPIs + DataTable ordenable + filtro por fechas", "auto", "test_resumen_agrega_por_periodo_y_mora_residual"),
    ("reimpresion-egresos", "Busca transacciones de egresos", "Reimpresión de comprobante por fila (consolida los 6 reimp* de VFP —créditos/seguros/premios/subsidios/varios/administración— en un solo visor sobre el buscador de egresos existente); GET /egresos/{id}/comprobante-pdf usa recibo_reimpresion_pdf", "auto", "test_reimpresion_comprobante_egreso_pdf"),
    # QA profundo — persistencia real en base (no sólo la API)
    ("deep-desembolso", "QA profundo (persistencia)", "Desembolso persiste pp_contrato ACTIVO, 12 cuotas (Σcapital=monto, cierra en 0), actividad DISBURSEMENT y asiento balanceado", "auto", "test_desembolso_persiste_todo"),
    ("deep-pago", "QA profundo (persistencia)", "El pago persiste cuota PAGADA/pagado, baja el saldo por el capital y guarda la actividad + asiento", "auto", "test_pago_persiste_cuota_actividad_y_asiento"),
    ("deep-reversa", "QA profundo (persistencia)", "Reversa marca la actividad REVERSADA en DB, crea REVERSAL, restaura la cuota y es idempotente (no duplica)", "auto", "test_reversa_persiste_y_es_idempotente"),
    ("deep-refi-coherencia", "QA profundo (persistencia)", "La simulación de refinanciación == el contrato persistido cuota a cuota (capital/interés/total) y en totales; viejo REFINANCIADO", "auto", "test_refinanciacion_simulacion_igual_a_persistido"),
    ("deep-drift", "QA profundo (persistencia)", "El recompute es determinista: releer el contrato da el mismo estado (sin drift) tras pago + prepago", "auto", "test_recompute_determinista_sin_drift"),
    # End-to-end: de la creación de la línea al cierre
    ("e2e-linea-cierre", "Ciclo de vida", "E2E por sistema (FRANCES/ALEMAN/AMERICANO/BULLET): crear línea → publicar → solicitud → aprobar → originar → desembolsar → cobrar → CERRADO, con asserts de persistencia en cada hito", "auto", "test_e2e_linea_a_cierre_con_persistencia"),
    ("e2e-situaciones", "Ciclo de vida", "E2E con vida rica: pago + parcial + prepago + diferimiento persistidos → payoff → CERRADO en DB", "auto", "test_e2e_con_situaciones_de_pago_hasta_payoff"),
    # Caja de créditos
    ("caja-medio", "Caja de créditos", "El cobro guarda el medio de pago para el recibo", "auto", "test_cobro_caja_registra_medio_pago"),
    ("caja-adelanto", "Caja de créditos", "Adelanto: paga N cuotas de una (N asientos), saldo baja por el capital", "auto", "test_adelanto_de_n_cuotas"),
    # Ciclo de vida completo (QA end-to-end)
    ("ciclo-sistemas", "Ciclo de vida", "Ciclo completo por sistema (crear→solicitud→originar→desembolsar→cobrar→CERRADO)", "auto", "test_ciclo_completo_por_sistema"),
    ("ciclo-cancelacion", "Ciclo de vida", "Cancelación anticipada (payoff) cierra el préstamo, asientos balanceados", "auto", "test_ciclo_con_cancelacion_anticipada"),
    ("ciclo-refinanciacion", "Ciclo de vida", "Refinanciación + cancelación del nuevo contrato hasta CERRADO", "auto", "test_ciclo_con_refinanciacion"),
    ("ciclo-combinado", "Ciclo de vida", "Operaciones entremezcladas (pago/parcial/mora/prepago/diferimiento/reversa/adelanto/payoff) con invariantes e idempotencia", "auto", "test_operaciones_combinadas_y_reversa"),
    ("caja-ui", "Caja de créditos", "Pantalla: elegir contrato → próxima cuota/saldo → cobrar (total/parcial/prepago) con medio de pago → recibo + asiento", "manual", ""),
    ("ori-mora", "Originar Crédito", "Cuota vencida cobra punitorio (moraTNA · días) y el asiento balancea", "auto", "test_mora_punitorio_en_cuota_vencida"),
    ("ori-sin-mora", "Originar Crédito", "Cuota al día (o dentro de gracia) no cobra punitorio", "auto", "test_sin_mora_si_cuota_al_dia"),
    ("ori-relacion-inv", "Originar Crédito", "Relación inexistente se rechaza (no ensucia el snapshot)", "auto", "test_relacion_invalida_rechaza"),
    ("ori-backdating", "Originar Crédito", "Backdating y reversa de actividades", "auto", "test_backdating_y_reversa"),
    ("ori-export", "Originar Crédito", "Export de contrato (PDF) y cartera (Excel)", "auto", "test_export_pdf_y_excel"),
    # Contabilidad (integración)
    ("cont-asientos", "Contabilidad", "Asientos de originación/pago balanceados en el Libro Diario", "auto", "test_asientos_contables_de_originacion_y_pago"),
    ("cont-reversa", "Contabilidad", "Contra-asiento de reversa (no borra el original)", "auto", "test_reversa_de_pago_genera_contra_asiento"),
    ("cont-devengo", "Contabilidad", "Devengamiento no duplica el ingreso", "auto", "test_devengamiento_no_duplica_ingreso"),
    ("cont-balance", "Contabilidad", "Todo asiento (otorgamiento/devengo/pago/mora/payoff) balancea debe=haber", "auto", "test_todos_los_asientos_balancean_en_el_ciclo"),
    # Maestros
    ("mae-catalogos", "Maestros", "Catálogo de segmentos/canales/relaciones disponible", "live", ""),
    ("mae-indices", "Maestros", "El índice BADLAR está en el maestro de índices", "live", ""),
    ("mae-impuestos", "Maestros", "Hay impuestos sembrados en el maestro (IVA, etc.)", "live", ""),
    ("mae-feriados", "Maestros", "Calendario de feriados AR sembrado (año actual) para el motor", "live", ""),
    ("mae-feriados-motor", "Maestros", "El motor saltea un feriado del maestro al fechar vencimientos", "auto", "test_preview_respeta_feriado_del_maestro"),
    ("mae-feriados-tipos", "Maestros", "Cálculo local fija tipos (Año Nuevo=INAMOVIBLE, Carnaval=TRASLADABLE) — colorea la UI", "auto", "test_calculo_local_ar_tipos"),
    # Feriados (pantalla) — casos de UI, verificación manual
    ("fer-ui-calendario", "Feriados (pantalla)", "Calendario: celdas cuadradas uniformes; feriados coloreados por tipo; el mes en curso tiene borde verde + '● actual' y el día de hoy un anillo verde (regresión: la clase de celda no debe colisionar con el contenedor .fer)", "manual", ""),
    ("fer-ui-leyenda", "Feriados (pantalla)", "Leyenda de colores visible (Inamovible/Trasladable/Puente/No laborable) y toggle Tabla/Calendario bajo 'Agregar manual'", "manual", ""),
    ("fer-ui-orden", "Feriados (pantalla)", "Tabla ordenable por columnas (fecha/nombre/tipo/origen/activo)", "manual", ""),
    ("fer-ui-importar", "Feriados (pantalla)", "Botón 'Importar de fuente oficial' arriba a la derecha; importa el año seleccionado", "manual", ""),
    # Auditoría de cambios (sistema nuevo) — idea incorporada del memo de migración de créditos
    ("auditoria-cambio-alta", "Auditoría de cambios", "Una mutación sensible (alta de solicitud, originación, baja) deja un rastro rico: usuario, IP (X-Forwarded-For), entidad, operación, resultado y el estado antes/después con su diff. Distinto del log VFP migrado (sólo el hecho). H-117", "auto", "test_alta_solicitud_deja_auditoria_con_ip"),
    ("auditoria-cambio-rechazo", "Auditoría de cambios", "Los rechazos también se auditan: una baja rechazada por regla / una solicitud con cliente inexistente quedan como resultado RECHAZADO/ERROR. El registro nunca interrumpe el negocio (falla en silencio ante error propio). H-117", "auto", "test_mutacion_rechazada_queda_auditada"),
    ("auditoria-cambio-pago-aprobacion", "Auditoría de cambios", "La cobertura se extendió a las demás mutaciones que dinamiza el memo: PAGAR (pago/prepago/payoff de contrato), COBRAR/ANULAR (cobranza y anulación de recibo) y APROBAR/RECHAZAR (workflow cuatro-ojos). Cada una deja su rastro con antes/después + IP. H-118", "auto", "test_pago_contrato_deja_auditoria"),
    # Portal del ciudadano (Fase 1) — idea #2 del memo migra_creditos.pdf
    ("portal-sso-realm", "Portal del ciudadano", "App pública separada (:5174). SSO con Mi Catamarca (OIDC Authorization Code, cliente confidencial) emite un token de sesión con scope 'portal', segregado del backoffice: un token de ciudadano NO abre endpoints internos y viceversa. Proveedor real por entorno o MOCK determinista en dev/tests. H-119", "auto", "test_realms_separados / test_flujo_sso_mock_emite_sesion"),
    ("portal-simulador-motor-unico", "Portal del ciudadano", "El simulador del portal corre sobre PRODUCTOS PUBLICADOS del product builder (pp_*, versión efectiva) y reusa el mismo `cronograma` que la originación del contrato → simulado == contratado. NO usa las LineaCredito legacy. Read-only en Fase 1. H-119", "auto", "test_simulador_usa_producto_nuevo_y_motor_unico"),
    ("portal-solo-publicado-vigente", "Portal del ciudadano", "El portal muestra SÓLO productos PUBLICADOS y vigentes hoy (vigente_desde ≤ hoy < vigente_hasta); se quitó el fallback a 'última publicada' para el ciudadano. Un borrador/revisión/aprobado/retirado o una versión publicada a futuro/vencida NO aparece. H-120", "auto", "test_simulador_usa_producto_nuevo_y_motor_unico"),
    ("portal-tna-variable-unica", "Portal del ciudadano", "Tasa variable: la simulación del portal y la prueba en vivo coincidían mal porque el portal usaba la TNA fija (0% en BADLAR). Se unificó en `_tna_base` (fija = default, VARIABLE = índice + margen), usado por originación, simulación pp y portal → simulado == contratado también en tasa variable. H-120", "auto", "test_simulador_usa_producto_nuevo_y_motor_unico"),
    ("cfgc-vigente-portal", "Configurar Créditos", "La tarjeta del catálogo muestra el estado de la ÚLTIMA versión y ADEMÁS qué versión está vigente HOY en el portal (`vigentePortal`): 'EN REVISIÓN · 🌐 portal: v2' cuando la última está en revisión pero una anterior sigue publicada/vigente, o 'no ofrecido' si ninguna versión está publicada y vigente. Aclara la conducta de versionado sin downtime (la v2 se sigue ofreciendo mientras se prepara la v3). H-121", "manual", ""),
    # Portal Fase 2 — el ciudadano envía la solicitud al backoffice
    ("portal-envia-solicitud", "Portal del ciudadano", "Fase 2: el ciudadano envía su solicitud desde el portal → se crea una PPSolicitud NO_REGISTRADO (alta express con la identidad de Mi Catamarca) directamente EN_EVALUACION, con origen PORTAL, y cae en el Inbox del backoffice para el pipeline cuatro-ojos (evaluar → aprobar → originar). La cuota que vio al simular se guarda en la solicitud. H-122", "auto", "test_ciudadano_envia_solicitud_cae_en_inbox"),
    ("portal-solicitud-idempotente", "Portal del ciudadano", "El envío de la solicitud lleva Idempotency-Key: un doble-clic no crea dos solicitudes (con_idempotencia); el Nº SOL-AAAA-NNNNN es único ante concurrencia (crear_con_numero_unico + constraint DB). 'Mis solicitudes' devuelve sólo las del propio ciudadano (marca portal:<sub>); un token interno no entra (realm separado). H-122", "auto", "test_envio_solicitud_es_idempotente / test_mis_solicitudes_solo_las_propias"),
    # Portal Fase 3 — datos del solicitante + elegibilidad + seguimiento
    ("portal-datos-elegibilidad", "Portal del ciudadano", "Fase 3: el ciudadano declara situación laboral (segmento), edad, antigüedad y sueldo. La simulación devuelve elegibilidad (mismo _elegibilidad del backoffice, canal WEB) y afectación (cuota/sueldo). Si no cumple, muestra los motivos claros (ej. 'Canal WEB no habilitado' / 'Segmento no habilitado'); igual puede enviar y un asesor revisa. Los datos viajan en la solicitud → el backoffice la evalúa bien (ya no ELEGIBLE ✕ vacío). H-124", "auto", "test_simular_con_datos_evalua_elegibilidad_y_afectacion / test_solicitud_guarda_datos_y_detalle"),
    ("portal-detalle-seguimiento", "Portal del ciudadano", "Fase 3: el ciudadano abre el detalle/seguimiento de cada solicitud (owner-scoped por su marca): estado, datos declarados, afectación y el cronograma estimado; si fue RECHAZADA ve el motivo. GET /portal/solicitudes/{numero} con 404 para ajenas. H-124", "auto", "test_solicitud_guarda_datos_y_detalle / test_detalle_404_ajeno"),
    ("portal-wizard-3-pasos", "Portal del ciudadano", "La solicitud del ciudadano es un proceso guiado de 3 pasos con stepper: (1) Tus datos → (2) Simulación (elegir producto/monto/plazo + ver cuota/elegibilidad) → (3) Confirmación (resumen + enviar). Cambiar el producto/monto/plazo invalida la simulación (hay que rehacerla); el paso 1 exige la situación laboral. UX, sin cambios de backend. H-125", "manual", ""),
    ("portal-documentacion-adjunta", "Portal del ciudadano", "Documentación adjunta (DNI, recibo) por solicitud EN_EVALUACION: los endpoints (subir/listar/borrar/descargar, owner-scoped, JPG/PNG/WEBP/PDF ≤5 MB, ≤10; bytes en pp_solicitud_documento) siguen vigentes y el asesor la ve/descarga en el backoffice (Solicitudes de crédito). H-131: se QUITÓ del PORTAL la carga de adjuntos en 'Mis solicitudes' (el ciudadano ya no sube desde el detalle); el backend se conserva para el backoffice. H-126", "auto", "test_documento_subir_listar_descargar / test_documento_valida_formato_y_owner"),
    ("portal-haberes-provider", "Portal del ciudadano", "Provider de haberes desacoplado (idea #2 del memo): `app/services/haberes.py` con implementación REAL (por `HABERES_API_URL`/token, cuando exista) o MOCK determinista. `GET /portal/haberes` autocompleta sueldo/antigüedad/relación; el botón 'Traer mis datos de Mi Catamarca' rellena el paso 1 y marca si son verificados o de demostración. La solicitud guarda `haberes_fuente` (declarado/micatamarca); el backoffice muestra 'sueldo verificado ✓ Mi Catamarca'. Listo para enchufar el API real por entorno. H-127", "auto", "test_haberes_mock_disponible / test_solicitud_registra_fuente_de_haberes"),
    ("portal-mis-creditos", "Portal del ciudadano", "El ciudadano ve sus créditos OTORGADOS (originados desde sus solicitudes, vía PPSolicitud.contrato_id): tarjeta con progreso de cuotas, saldo y próxima cuota (marca 'En mora' si hay vencidas); el detalle muestra el cronograma con el estado de cada cuota (Pagada/Pendiente/Vencida). Owner-scoped (404 para ajenos). H-128", "auto", "test_mis_creditos_y_notificaciones"),
    ("portal-notificaciones", "Portal del ciudadano", "Feed de notificaciones del ciudadano derivado del estado de sus créditos: otorgamiento reciente, próximo vencimiento (≤7 días) y cuota vencida. Campana con contador en el header. GET /portal/notificaciones. H-128", "auto", "test_mis_creditos_y_notificaciones"),
    ("portal-pre-aprobado", "Portal del ciudadano", "UX fintech (BBVA/Ualá): pre-aprobado 'cuánto puedo pedir'. `POST /portal/pre-aprobado` busca por bisección sobre el motor único el mayor monto cuya cuota no supera la afectación (cuota ≤ %·sueldo). El portal muestra 'Podés pedir hasta $X' + 'Usar el máximo'. H-129", "auto", "test_pre_aprobado_respeta_afectacion"),
    ("portal-slider-en-vivo", "Portal del ciudadano", "UX fintech: en el paso 2, monto y cuotas son SLIDERS y la cuota se recalcula EN VIVO (debounce), sin apretar 'Simular'. Se quitó el botón de simular manual. H-129", "manual", ""),
    ("portal-cbu-consentimientos", "Portal del ciudadano", "Para enviar la solicitud se exige el CBU de acreditación (22 dígitos) y dos consentimientos explícitos (términos y condiciones + tratamiento de datos personales). `enviar_solicitud` valida (422 sin consentimientos o CBU ≠ 22 dígitos) y persiste en datos_adicionales `cbu` + `consentimiento {terminos, datos, fecha}`; el botón 'Confirmar y enviar' queda deshabilitado hasta completarlos. El input del CBU acepta SOLO dígitos (descarta letras/símbolos al tipear o pegar) y corta en 22 (no deja cargar más). H-130", "auto", "test_ciudadano_envia_solicitud_cae_en_inbox / test_envio_solicitud_es_idempotente"),
    ("portal-cta-visible-responsive", "Portal del ciudadano", "El paso 2 colapsa el cronograma en un <details> y suma una barra sticky al pie con la cuota + 'Continuar →' (siempre a la vista). El portal es responsive: sin scroll horizontal a 375 px (html,body overflow-x hidden), header con flex-wrap y media queries a 680/400 px. H-130", "manual", ""),
    ("portal-tracking-expediente", "Portal del ciudadano", "El detalle de 'Mis solicitudes' abre con un stepper de seguimiento del trámite: Enviada → En evaluación → Aprobada → Otorgada (y Enviada → En evaluación → Rechazada si se rechaza). Las etapas se DERIVAN del estado de la PPSolicitud (sin cambio de esquema): superadas en verde ✓, la actual en navy, pendientes en gris, rechazo en rojo ✕. H-132", "manual", ""),
    ("portal-destino-credito", "Portal del ciudadano", "El ciudadano elige (opcional) el destino del crédito en el paso 1 ('¿para qué lo necesitás?': Vivienda/Vehículo/Consumo/Educación/Salud/Refinanciación/Emprendimiento/Otro). `DESTINOS`+`_destino_norm` en portal.py son la fuente de verdad (normaliza a mayúsculas, descarta desconocidos); se persiste el código en datos_adicionales y el detalle devuelve la etiqueta. Se ve en el resumen de confirmación, en el detalle y en el backoffice (Solicitudes de crédito) para la evaluación. H-133", "auto", "test_solicitud_guarda_destino"),
    ("originacion-web-revision", "Solicitudes / Originación", "Una solicitud del canal web (origen PORTAL) entra express: hay que revisar que llegue con TODO lo necesario para liquidar antes de originar. `enviar_solicitud` arrastra el DNI de Mi Catamarca al cliente_datos; `_datos_liquidacion` calcula el checklist 'listo para liquidar' (obligatorios: apellido/nombre + DNI + CBU 22 díg.; deseables: CUIL, sueldo) y se expone en el serial (datosLiquidacion). `originar` BLOQUEA (422) una solicitud web incompleta, listando los faltantes; el backoffice muestra el panel de revisión y deshabilita 'Originar contrato'. H-134", "auto", "test_originacion_web_es_revision_y_bloquea_sin_datos"),
    ("originacion-desde-solicitud-a-liquidar", "Solicitudes / Originación", "Originar DESDE UNA SOLICITUD nunca desembolsa en el acto: el contrato queda A_LIQUIDAR (se ignora el flag `desembolsar` en ese camino; la originación directa sin solicitud lo mantiene, p. ej. servicing). Desde el backoffice, 'Originar contrato' es una confirmación de la revisión (no reingresa datos) y avisa que queda A_LIQUIDAR. H-135", "auto", "test_originacion_deja_a_liquidar_y_lote_desembolsa"),
    ("liquidacion-por-lote", "Créditos / Liquidación", "Los contratos A_LIQUIDAR se agrupan por DÍA de originación (`GET /contratos/lotes-liquidacion`) y se liquidan juntos (`POST /contratos/liquidar-lote` con la fecha): cada uno pasa a desembolso respetando el workflow DESEMBOLSO (los que requieran aprobación quedan pendientes). Pantalla nueva 'Liquidación por lote' (lista de lotes por día → detalle de contratos → liquidar). H-135", "auto", "test_originacion_deja_a_liquidar_y_lote_desembolsa"),
    ("solicitud-alta-wizard", "Solicitudes / Alta guiada", "'Nueva solicitud' del backoffice es una ventana flotante con 3 pasos (Solicitante → Simulación → Confirmación), como el alta del ciudadano. La simulación usa `POST /productos/{id}/simular-preview`: mismo motor único que la originación pero SIN persistir (no ensucia las simulaciones guardadas), y devuelve cuota + elegibilidad. La solicitud se crea en BORRADOR. El cliente se ELIGE del maestro con un buscador typeahead (H-144, mismo criterio que Originar): no se carga a mano; el alta de clientes vive en Clientes → Maestro. El alta express NO_REGISTRADO sigue existiendo sólo para el portal y su promoción a maestro. H-136", "auto", "test_simular_preview_no_persiste_y_evalua"),
    ("alta-maestro-cuil", "Solicitudes / Alta express", "'Dar de alta en maestro' de una solicitud express es una mini-revisión: precarga apellido/nombre y DNI declarados (el DNI viaja desde Mi Catamarca) y el asesor completa/confirma el CUIL. `promover_cliente` valida el CUIL (11 dígitos), normaliza dígitos, deduplica por CUIL y crea el Cliente en el maestro; la solicitud pasa a REGISTRADA. H-137", "auto", "test_alta_maestro_completa_cuil"),
    ("originacion-unificada", "Créditos / Originación", "Circuito unificado (H-143): 'Originar Crédito' es SOLO instrumentación — el contrato queda A_LIQUIDAR y el desembolso pasa siempre por Liquidación por lote. Se quitó el paso 5 de desembolso directo de OriginarCredito (antes convivían dos caminos al desembolso). Alinea con banca: decisión de crédito separada de la liquidación/desembolso, con control de liquidación por tanda diaria. Además, el cliente ya NO se carga a mano: se ELIGE del maestro con un buscador typeahead (el alta vive en Clientes → Maestro).", "manual", ""),
    ("iam-seed-roles", "Seguridad / IAM", "El maestro de Roles (perfiles) se siembra en el arranque (`seed_perfiles`, idempotente): sin él la pantalla Seguridad → Roles quedaba vacía tras un reset y los roles asignados a los usuarios (ADMG/XCR/XCJ) no tenían ficha en el catálogo. Se siembran ADMG, XCR, XCJ, XCA, XTE, XSE, XDE, XME; el maestro muestra el conteo de usuarios por rol. Menú Seguridad ordenado: Usuarios · Grupos · Roles. H-142", "manual", ""),
    ("situacion-centrada-cliente", "Créditos / Servicing", "Situación del cliente es CENTRADA EN EL CLIENTE (H-149): al buscar, los contratos se agrupan por cliente en una tarjeta con N préstamos, activos, en mora y saldo total; recién ahí se elige el contrato para operar (se expande el servicing). Antes era una lista plana que mezclaba clientes; con un cliente de varios préstamos no había visión consolidada.", "manual", ""),
    ("servicing-dedup-y-overflow", "Créditos / Servicing", "Situación del cliente (H-148): (1) `postIdem` deduplicaba 4 s tras responder → una 2ª acción idéntica (diferir otra cuota, pagar la siguiente) devolvía el resultado viejo y se perdía; se cambió a dedup SÓLO en vuelo (protege el doble-submit concurrente, la Idempotency-Key + backend son el árbitro real). (2) El detalle expandido desbordaba la página (~1278 px); se agregó overflow-x:auto a la tabla y `.sv-body` responsive (min-width:0, stack &lt;900px). Las acciones de servicing en sí ya funcionaban bien (backend + UI).", "manual", ""),
    ("portal-dark-mode", "Portal del ciudadano", "El portal es theme-aware (H-147): respeta el modo oscuro del dispositivo con un bloque @media (prefers-color-scheme: dark) que redefine los tokens --p-* (navy más claro + verde) y ajusta los fondos claros hardcodeados. Antes era sólo claro. Light intacto; responsive a 375 px OK en ambos temas.", "manual", ""),
    ("validaciones-portal-rangos", "Portal del ciudadano", "Los datos declarados del ciudadano se acotan en el backend (H-146): edad 18-99, antigüedad ≥0, sueldo >0 (Field ge/le/gt en DatosSolicitante). Antes los límites eran sólo HTML 'blandos'. /portal/simular rechaza (422) valores fuera de rango.", "auto", "test_portal"),
    ("dialogos-in-app", "UX / Diálogos", "H-152: se reemplazaron TODOS los window.confirm/alert/prompt nativos (el cartel 'localhost dice…') por un módulo in-app `src/ui/dialog.tsx` (confirmar/avisar/pedirTexto): modal centrado con el tema de la app, Esc cancela, Enter acepta, clic en el fondo cierra, variante danger para irreversibles. Cubre ~14 pantallas (originar, liquidar lote, baja de cliente, reversar, payoff, refinanciar, migradores, borrar rol/grupo/feriado, reset de clave, etc.). El alta/edición de cliente además cierra con Esc.", "manual", ""),
    ("cliente-modal-centrado", "Clientes", "Maestro de clientes (H-151): el alta/edición de cliente abre como ventana flotante CENTRADA (modal) en el medio de la pantalla —no como panel lateral—, con scrim, esquinas redondeadas, max-height 90vh y scroll interno (header/footer fijos). Cambio scopeado a `.drawer`/`.drawer-scrim` (únicas usuarias = Maestro de clientes).", "manual", ""),
    ("validaciones-clientes", "Clientes / Validaciones", "Maestro de clientes (H-145): CUIL validado por dígito verificador en el front (mismo algoritmo que el backend, cierra el desajuste que devolvía 422); DNI solo dígitos 7-8, email con formato, sueldo numérico ≥0, CBU 22 dígitos — cada uno con hint y gateando Crear/Guardar. Asteriscos en Apellido y nombre y CUIL. Backend `ClienteBase`: apellido_nombre min_length=1 y sueldo ge=0.", "manual", ""),
    ("validaciones-obligatorios-1", "QA / Validaciones", "Primera pasada de validaciones y campos obligatorios (H-141): backend `SolicitudIn` con `Field(gt=0)` en monto y `gt=0,le=240` en plazo; wizard Nueva solicitud (express) exige CUIL 11 díg (gate + solo dígitos) alineado al 422 del backend + asteriscos en obligatorios; OriginarCredito exige CBU de acreditación (22 díg) para avanzar → cierra el hueco de H-134 en originación directa. Pendiente: Clientes.tsx (DNI/email/sueldo/CBU + DV CUIL), portal edad/sueldo, unificar desembolso. Detalle en salida/qa-visual-2026-09-09.md.", "manual", ""),
    ("workflow-single-admin", "QA / Workflow", "Hallazgo E2E (H-141): con un solo usuario ADMG, una solicitud/línea cargada en BACKOFFICE no se podía aprobar/publicar (el nivel exige ADMG y el emisor no puede aprobar por separación de funciones). RESUELTO: el cuatro-ojos de LINEA y SOLICITUD ahora se SIEMBRA INACTIVO (`seed_workflow`), así un único admin opera de entrada; se activa desde Seguridad → Workflow cuando la org suma un 2º aprobador (DESEMBOLSO y REFINANCIACION ya venían inactivos). El portal nunca lo sufrió (crea como portal:<sub>).", "manual", ""),
    ("portal-guardar-borrador", "Portal del ciudadano", "El ciudadano puede guardar la solicitud a medias ('Guardar borrador') y retomarla después desde el mismo dispositivo: el estado del wizard (datos/producto/monto/plazo/CBU/consentimientos/paso) se persiste en localStorage por sub. Al volver, un banner 'Tenés una solicitud sin terminar' ofrece Retomar/Descartar; al enviar la solicitud el borrador se limpia. No crea PPSolicitud BORRADOR (no ensucia el Inbox del backoffice). H-140", "manual", ""),
    ("liquidacion-lote-pendientes", "Créditos / Liquidación", "La pantalla de Liquidación por lote marca los contratos que ya están esperando la aprobación del workflow DESEMBOLSO: `lotes-liquidacion` agrega `pendienteAprobacion` por contrato y `pendientes` por lote (contando PPWorkflowPendiente objeto=DESEMBOLSO abiertos). La UI muestra un pill 'esperando aprobación' y un aviso de que se desembolsan al aprobarse en el Inbox y que volver a liquidar no los duplica. H-139", "auto", "test_lote_marca_pendientes_de_aprobacion"),
    ("sidebar-modulos-ocultos", "Navegación / Sidebar", "Módulos marcados `oculto` (Despacho, Caja, Juegos/Quiniela, Mesa de Entradas, Seguros, Adm. y Finanzas) se esconden por defecto. Créditos es `soloNuevos`: sólo muestra las opciones `nuevo`; las heredadas del legacy quedan ocultas. Sólo el ADMINISTRADOR (permisos.sinRestricciones = ADMG) ve un botón en el sidebar que revela TANTO los módulos ocultos como las opciones heredadas; la preferencia se guarda en localStorage. Un no-admin nunca las ve. Además se quitaron las leyendas de grupo (Archivos/Datos/Procesos/Consultas/Reportes) del sidebar. Controles de Versión queda SIEMPRE visible. H-138", "manual", ""),
]


def _run_live(cid: str, db) -> tuple[bool, str]:
    from datetime import date as _date
    from app.api import contratos as C, productos as P
    from app.api.productos import PreviewIn

    def prev(**kw):
        base = dict(sistema="FRANCES", monto=1000000, plazo=12, tna=52, cargoOtorg=0)
        base.update(kw)
        return P.preview(PreviewIn(**base), db=db)

    # ---- oferta / segmentación ----
    if cid == "ori-oferta":
        cods = {p["codigo"] for p in C.oferta(db=db)["items"]}
        ok = {"LP-PERS-01", "LP-JUB-01"} <= cods and "LP-ADEL-01" not in cods and "LP-VIV-01" not in cods
        return ok, "ofrecidas: " + ", ".join(sorted(cods))
    if cid == "ori-segmento":
        of = {p["codigo"]: p for p in C.oferta(db=db, segmento="JUBILADO")["items"]}
        ok = of["LP-JUB-01"]["elegibilidad"]["elegible"] and not of["LP-PERS-01"]["elegibilidad"]["elegible"]
        return ok, "JUBILADO: Jubilados elegible, Personal no"
    if cid == "ori-segmento-ap":
        of = {p["codigo"]: p for p in C.oferta(db=db, segmento="AGENTE_PUBLICO")["items"]}
        ok = of["LP-PERS-01"]["elegibilidad"]["elegible"] and not of["LP-JUB-01"]["elegibilidad"]["elegible"]
        return ok, "AGENTE_PUBLICO: Personal elegible, Jubilados no"
    if cid == "ori-canal":
        of = {p["codigo"]: p for p in C.oferta(db=db, canal="CONVENIO")["items"]}
        ok = of["LP-JUB-01"]["elegibilidad"]["elegible"] and not of["LP-PERS-01"]["elegibilidad"]["elegible"]
        return ok, "canal CONVENIO: Jubilados sí, Personal no"
    if cid == "ori-edad":
        of = {p["codigo"]: p for p in C.oferta(db=db, edad=30)["items"]}
        ok = not of["LP-JUB-01"]["elegibilidad"]["elegible"]
        return ok, "edad 30: Jubilados (mín. 60) no elegible"
    if cid == "ori-variable":
        var = next(p for p in C.oferta(db=db)["items"] if p["codigo"] == "LP-VAR-01")
        cfg = var["cfg"]
        # La TNA vigente debe resolver índice + margen (no quedar en la default 0).
        esperado = cfg.get("margen", 0) + 45  # BADLAR sembrado en 45%
        ok = cfg["modalidad"] == "VARIABLE" and cfg.get("indice") == "BADLAR" and abs(cfg.get("tnaVigente", 0) - esperado) < 0.01 and cfg["tna"] == 0
        return ok, f"LP-VAR-01 · TNA vigente {cfg.get('tnaVigente')}% = BADLAR + margen {cfg.get('margen')}% (default {cfg['tna']})"
    if cid == "ori-bundle":
        bs = C.bundles(db=db)["items"]
        ok = any(x["codigo"] == "BND-CAP-01" and len(x["miembros"]) >= 2 for x in bs)
        return ok, f"{len(bs)} bundle(s) · BND-CAP-01 con miembros"
    if cid == "ori-tablero":
        t = C.tablero(db=db)
        ok = t["saldoVigente"] <= t["capitalColocado"] + 0.01 and t["cuotasPagadas"] >= 0
        return ok, f"{t['contratos']} contratos · saldo vigente {t['saldoVigente']:.0f}"
    # ---- maestros ----
    if cid == "mae-catalogos":
        cat = C.segmentos()
        ok = "JUBILADO" in cat["segmentos"] and any(r["codigo"] == "PREMIUM" for r in cat["relaciones"])
        return ok, f"{len(cat['segmentos'])} segmentos · {len(cat['relaciones'])} relaciones"
    if cid == "mae-indices":
        from app import models
        idx = db.query(models.IndiceReferencia).filter_by(codigo="BADLAR").first()
        return bool(idx), f"BADLAR = {float(idx.valor)}%" if idx else "no está BADLAR"
    if cid == "mae-impuestos":
        from app import models
        n = db.query(models.Impuesto).count()
        return n > 0, f"{n} impuestos en el maestro"
    if cid == "mae-feriados":
        from app import models
        from datetime import date as _d
        a = _d.today().year
        n = db.query(models.Feriado).filter(models.Feriado.pais == "AR",
              models.Feriado.fecha >= _d(a, 1, 1), models.Feriado.fecha <= _d(a, 12, 31)).count()
        return n >= 8, f"{n} feriados AR {a} en el maestro"
    # ---- cálculo de cuotas (opciones de préstamo) ----
    if cid == "calc-cierra":
        rows = prev(cargoOtorg=2)["rows"]
        scap = round(sum(x["capital"] for x in rows), 2)
        ok = len(rows) == 12 and abs(rows[-1]["saldo_final"]) < 0.01 and abs(scap - 1000000) < 0.5
        return ok, f"saldo final {rows[-1]['saldo_final']:.2f} · Σcapital {scap:.0f}"
    if cid == "calc-frances":
        rows = prev(sistema="FRANCES")["rows"]
        tots = [r["total"] for r in rows]
        ok = max(tots) - min(tots) < 1
        return ok, f"cuota constante ≈ {rows[0]['total']:.0f}"
    if cid == "calc-aleman":
        rows = prev(sistema="ALEMAN")["rows"]
        caps = [r["capital"] for r in rows[:-1]]
        ok = max(caps) - min(caps) < 1 and rows[0]["interes"] > rows[-1]["interes"]
        return ok, f"capital {caps[0]:.0f} constante · interés {rows[0]['interes']:.0f}→{rows[-1]['interes']:.0f}"
    if cid == "calc-americano":
        rows = prev(sistema="AMERICANO")["rows"]
        ints = [r["interes"] for r in rows]
        ok = rows[0]["capital"] == 0 and abs(rows[-1]["capital"] - 1000000) < 1 and max(ints) - min(ints) < 1
        return ok, f"capital sólo al final · interés {ints[0]:.0f} constante"
    if cid == "calc-bullet":
        rows = prev(sistema="BULLET")["rows"]
        ok = all(r["total"] == 0 for r in rows[:-1]) and rows[-1]["total"] > 1000000
        return ok, f"pago único {rows[-1]['total']:.0f} al vencimiento"
    if cid == "calc-gracia":
        rows = prev(gracia=3)["rows"]
        ok = all(rows[k]["capital"] == 0 and rows[k]["interes"] > 0 for k in range(3)) and rows[3]["capital"] > 0
        return ok, "3 cuotas de sólo interés, amortiza desde la 4ª"
    if cid == "calc-trimestral":
        rows = prev(frecuencia="TRIMESTRAL")["rows"]
        d0, d1 = _date.fromisoformat(rows[0]["fecha_vencimiento"]), _date.fromisoformat(rows[1]["fecha_vencimiento"])
        meses = (d1.year - d0.year) * 12 + (d1.month - d0.month)
        return len(rows) == 12 and meses == 3, f"vencimientos cada {meses} meses"
    if cid == "calc-adelantada":
        v = prev(tipoCuota="VENCIDA")["rows"]
        a = prev(tipoCuota="ADELANTADA")["rows"]
        ok = v[0]["interes"] > 0 and a[0]["interes"] == 0
        return ok, f"vencida 1er interés {v[0]['interes']:.0f} vs adelantada 0"
    if cid == "calc-cargo-desemb":
        rows = prev(cargoOtorg=3, cargoMomento="DESEMBOLSO")["rows"]
        ok = rows[0]["cargos"] > rows[-1]["cargos"] * 2 + 1
        return ok, f"1ª cuota cargos {rows[0]['cargos']:.0f} >> resto {rows[-1]['cargos']:.0f}"
    if cid == "calc-cargo-prorr":
        rows = prev(cargoOtorg=3, cargoMomento="PRORRATEADO")["rows"]
        ok = abs(rows[0]["cargos"] - rows[-1]["cargos"]) < 1
        return ok, f"cargos iguales por cuota ({rows[0]['cargos']:.0f})"
    if cid == "calc-financiable":
        b = round(sum(r["capital"] for r in prev(cargoOtorg=5, cargoMomento="DESEMBOLSO", financiable=False)["rows"]), 0)
        f = round(sum(r["capital"] for r in prev(cargoOtorg=5, cargoMomento="DESEMBOLSO", financiable=True)["rows"]), 0)
        ok = abs(b - 1000000) < 1 and f > 1000000 + 1000
        return ok, f"amortiza {f:.0f} (monto + cargo) vs {b:.0f}"
    if cid == "calc-iva-interes":
        sin = prev(cargoOtorg=2)["resumen"]["totalCuotas"]
        con = prev(cargoOtorg=2, impuestos=[{"base": "INTERES", "porcentaje": 21}])["resumen"]["totalCuotas"]
        return con > sin, f"sin IVA {sin:.0f} < con IVA {con:.0f}"
    if cid == "calc-iva-cargos":
        sin = prev(cargoOtorg=3)["resumen"]["totalCuotas"]
        con = prev(cargoOtorg=3, impuestos=[{"base": "CARGOS", "porcentaje": 21}])["resumen"]["totalCuotas"]
        return con > sin, f"sin IVA {sin:.0f} < con IVA {con:.0f}"
    if cid == "calc-ajuste-finde":
        rows = prev(ajusteFinDeSemana="SIGUIENTE_HABIL", primerVencimientoDias=30, diaPago=6, plazo=24)["rows"]
        findes = [r["fecha_vencimiento"] for r in rows if _date.fromisoformat(r["fecha_vencimiento"]).weekday() >= 5]
        return len(findes) == 0, f"0 vencimientos en fin de semana (de {len(rows)})"
    if cid == "calc-dia-pago":
        a = prev(diaPago=5)["rows"][1]["fecha_vencimiento"]
        b = prev(diaPago=20)["rows"][1]["fecha_vencimiento"]
        return a != b, f"día 5 → {a} · día 20 → {b}"
    if cid == "calc-feriado":
        from app.services.productos_calc import cronograma as _cron
        # 1er venc caería 2026-01-01 (Año Nuevo); con SIGUIENTE_HABIL debe rodar al 02-01.
        f = _cron("FRANCES", 100000, 3, 52, fecha_valor=_date(2025, 12, 2), dia_pago=1,
                  primer_venc_dias=30, ajuste_fin_semana="SIGUIENTE_HABIL")
        d0 = str(f[0]["fecha_vencimiento"])
        return d0 == "2026-01-02", f"1-ene (feriado) → {d0}"
    # ---- Sistema de cálculos ----
    if cid == "sc-catalogo":
        from app.api import sistema_calculos as SC
        cat = SC.catalogo(db=db)
        cert = cat["certificacion"]
        ok = len(cat["sistemas"]) == 4 and cert["certificado"] and len(cert["checksum"]) == 64
        return ok, f"{len(cat['sistemas'])} sistemas · checksum {cert['checksumCorto']} · redondeo {cert['reglaRedondeo']}"
    if cid == "sc-debug":
        from app.api import sistema_calculos as SC
        d = SC.debug(SC.DebugIn(sistema="FRANCES", monto=100000, plazo=6, tna=52))
        pasos = d["pasos"]
        ok = len(pasos) == 6 and pasos[-1]["saldoFinal"] == "0,00" and any("interés = saldo" in l for l in pasos[0]["detalle"])
        return ok, f"{len(pasos)} pasos · cierra en {pasos[-1]['saldoFinal']}"
    # ---- Situación del cliente (consulta consolidada) ----
    if cid == "sit-consolidada":
        s = C.situacion_cliente(q="", db=db)
        r = s["resumen"]
        ok = r["saldoVigente"] <= r["capitalColocado"] + 0.01 and r["activos"] <= r["contratos"]
        return ok, f"{r['contratos']} contratos · saldo {r['saldoVigente']:.0f} ≤ colocado {r['capitalColocado']:.0f}"
    if cid == "sit-mora-aldia":
        s = C.situacion_cliente(q="", db=db)
        # invariante: si un item reporta mora>0 debe estar ACTIVO y en mora; los cerrados no
        mal = [x for x in s["items"] if x["moraAlDia"] > 0 and not (x["estado"] == "ACTIVO" and x["enMora"])]
        return not mal, f"{s['resumen']['enMora']} en mora / {s['resumen']['contratos']} · sin inconsistencias" if not mal else f"{len(mal)} items con mora fuera de ACTIVO/vencido"
    if cid == "wf-reglas":
        from app.services import workflow as wf
        from app import models_productos as mp
        wf.seed_workflow(db)
        objs = {r.objeto: r for r in db.query(mp.PPWorkflowRegla).all()}
        ok = ({"LINEA", "SOLICITUD", "DESEMBOLSO", "REFINANCIACION"} <= set(objs)
              and objs["LINEA"].activo and not objs["DESEMBOLSO"].activo
              and all(len(r.niveles) >= 1 for r in objs.values()))
        return ok, f"{len(objs)} reglas · LINEA activo={objs['LINEA'].activo} · DESEMBOLSO activo={objs['DESEMBOLSO'].activo}"
    if cid == "arq-principios":
        p = principios()
        ids = {x["id"] for x in p["items"]}
        need = {"unicidad-concurrente", "trazabilidad-temporal", "idempotency-key", "cuatro-ojos"}
        ok = p["total"] >= 5 and need <= ids and all(
            x.get("titulo") and x.get("enunciado") and x.get("motivo") for x in p["items"])
        return ok, f"{p['total']} principios · incluye {', '.join(sorted(need & ids))}"
    if cid == "dis-principios":
        p = principios_diseno()
        ids = {x["id"] for x in p["items"]}
        ok = p["total"] >= 5 and "tabla-unica" in ids and all(
            x.get("titulo") and x.get("enunciado") and x.get("ejemplo") for x in p["items"])
        return ok, f"{p['total']} principios de diseño · incluye tabla-unica (con ejemplo)"
    return False, "caso desconocido"


# Opciones de menú nuevas.
MENU_NUEVO = [
    ("Créditos → Configurar Créditos", "/creditos/configurar", "Product builder de líneas de crédito"),
    ("Créditos → Originar Crédito", "/creditos/originar", "Proceso guiado de originación + servicing"),
    ("Créditos → Sistema de cálculos", "/creditos/sistema-calculos", "Fórmulas del motor + depurador paso a paso de cuotas"),
    ("Créditos → Solicitudes de crédito", "/creditos/solicitudes-credito", "Alta/evaluación de solicitudes (registrado o express) → originación"),
    ("Créditos → Liquidación por lote", "/creditos/liquidacion-lote", "Contratos A_LIQUIDAR agrupados por día de originación; se liquida el lote y pasa a desembolso"),
    ("Créditos → Caja de créditos", "/creditos/caja", "Cobranza de contratos: cobro total/parcial/prepago con medio de pago, recibo y asiento"),
    ("Créditos → Situación del cliente", "/creditos/situacion-linea", "Consulta consolidada por cliente + servicing completo del contrato (pago/parcial/prepago/diferimiento/refinanciación/payoff/reversa, plan, actividades y asientos)"),
    ("Créditos → Tablero de cartera", "/creditos/tablero-cartera", "Analítica de la cartera: KPIs + agrupación por estado/sistema/línea/rango de saldo con participación"),
    ("Créditos → Inbox de aprobaciones", "/creditos/inbox-aprobaciones", "Bandeja cuatro-ojos: tareas que esperan mi aprobación (líneas y solicitudes), con quién lo pidió y link para aprobar; alerta en la campana"),
    ("Contabilidad → Impuestos", "/contabilidad/impuestos", "Maestro de impuestos (lo usa el componente TAX)"),
    ("Contabilidad → Índices de referencia", "/contabilidad/indices", "Maestro de índices (tasa variable)"),
    ("Contabilidad → Feriados (calendario)", "/contabilidad/feriados", "Maestro de feriados por país; alimenta el ajuste a día hábil del motor"),
    ("Controles de Versión → Principios de arquitectura", "/controles-version/principios", "Principios que guían las decisiones de arquitectura de la app"),
    ("Seguridad → Workflow de aprobaciones", "/seguridad/workflow", "Motor de cuatro-ojos / N-ojos configurable por objeto (rol + overrides por usuario, niveles en serie)"),
    ("Controles de Versión → Principios de diseño", "/controles-version/principios-diseno", "Convenciones de diseño/UI con ejemplos (tabla única, layout ABM, badge new, pills…)"),
    ("Controles de Versión → Procesos", "/controles-version/procesos", "Procesos/mecanismos de calidad de la migración: candado de diseño, guardas de unicidad/idempotencia/balance, event-sourcing, equivalencia vs VFP, QA profundo, seguridad"),
    ("Seguridad → Auditoría de cambios", "/seguridad/auditoria-cambios", "Rastro de las mutaciones del sistema nuevo con antes/después + IP + resultado (distinto del log VFP migrado)"),
    ("Portal del ciudadano (app :5174)", "http://localhost:5174", "App PÚBLICA separada: login SSO Mi Catamarca (OIDC) + simulador sobre los PRODUCTOS del builder (pp_*, motor único). Mismo backend, otro origen/realm. Fase 1"),
]


# ---------------- Principios de arquitectura ----------------
# Criterios que guían TODA decisión de arquitectura. Se van sumando durante la construcción.
# Cada principio: id, titulo, enunciado (la regla), motivo (por qué), aplica (dónde), ref (hallazgo/caso).
PRINCIPIOS = [
    {"id": "unicidad-concurrente", "categoria": "Datos / Concurrencia",
     "titulo": "Unicidad concurrente: la base es el árbitro, no un lock aplicativo",
     "enunciado": "Los identificadores únicos (número de contrato, de solicitud, código de línea) se generan "
                  "como 'el primer libre' y se insertan dentro de un SAVEPOINT; ante colisión (dos usuarios "
                  "tomaron el mismo número), la constraint única de la DB lo rechaza y se REINTENTA con un "
                  "número fresco. Nunca un lock aplicativo global.",
     "motivo": "Calcular el próximo número y luego insertar es un TOCTOU: sin la constraint como árbitro, dos "
               "requests simultáneos generan el mismo id y el segundo rompe con 500. El reintento es simple, "
               "escala y no puede quedar colgado como un lock.",
     "aplica": ["Alta de línea, originar/refinanciar contrato, alta de solicitud, versión de producto",
                "Nºs de negocio legacy: recibo de caja, orden de pago, cobranza de quiniela, resolución, póliza, turno (H-108)",
                "Reversa de actividad: una sola vez (uq_pp_actividad_reversa_de, H-110)"],
     "ref": "H-097/H-108/H-110 · helper crear_con_numero_unico (app/core/numbering.py) · casos num-concurrencia, caja-recibo-unico, op-numero-unico, num-compuesto-unico"},
    {"id": "motor-unico", "categoria": "Cálculo",
     "titulo": "Un único motor de cálculo (una sola fuente de verdad)",
     "enunciado": "El cronograma de cuotas se calcula SIEMPRE con `cronograma()`. Preview, originación, "
                  "simulación de refinanciación y persistencia usan el mismo motor con los mismos parámetros.",
     "motivo": "Evita que 'lo simulado' difiera de 'lo contratado'. Lo que ve el usuario antes de confirmar es "
               "exactamente lo que se persiste.",
     "aplica": ["Simulador", "Originación", "Panel de refinanciación", "Sistema de cálculos"],
     "ref": "caso ori-coherencia · deep-refi-coherencia"},
    {"id": "event-sourcing", "categoria": "Servicing",
     "titulo": "Servicing event-sourced con recompute determinista",
     "enunciado": "Las actividades (`pp_actividad`) son la verdad. El estado del contrato se reconstruye "
                  "reseteando al cronograma pristino y reproduciendo las actividades. Reversar = marcar "
                  "REVERSADA y recomputar (idempotente).",
     "motivo": "Trazabilidad total, correcciones sin borrar historia, y un mismo input siempre da el mismo "
               "estado (sin drift). Verificado: _recompute es determinista (recomputar N veces = mismo estado) "
               "y una actividad se reversa UNA sola vez (constraint DB uq_pp_actividad_reversa_de frena la "
               "doble-reversa concurrente = doble contra-asiento, H-110).",
     "aplica": ["Pagos, prepago, diferimiento, payoff, repricing, reversa"],
     "ref": "H-110 · casos reversa-idempotente, recompute-determinista · _recompute (app/api/contratos.py)"},
    {"id": "snapshot-congelado", "categoria": "Producto",
     "titulo": "El contrato congela el producto (snapshot)",
     "enunciado": "Al originar, el contrato guarda un snapshot del producto/versión vigente. Cambios "
                  "posteriores de la línea NO alteran contratos ya vivos.",
     "motivo": "Un préstamo se rige por las condiciones al momento de otorgarse; versionar el producto no "
               "puede reescribir contratos existentes.",
     "aplica": ["Originación", "Vigencia por versión"],
     "ref": "caso cfg-vigencia · snapshot_producto"},
    {"id": "contabilidad-balanceada", "categoria": "Contabilidad",
     "titulo": "Todo asiento balancea; la reversa contra-asienta, no borra",
     "enunciado": "Cada evento contable genera un asiento con debe = haber. Una reversa produce un "
                  "contra-asiento; nunca se borra ni edita el asiento original. **Con guarda mecánica**: un "
                  "evento before_insert rechaza cualquier asiento de la app que no balancee (los del mayor "
                  "plano legacy de VFP, de una pierna, se excluyen).",
     "motivo": "Integridad contable y auditabilidad: el Libro Diario es inmutable hacia atrás; un bug de "
               "redondeo que desbalancee un asiento falla ruidoso, no corrompe el libro en silencio.",
     "aplica": ["Otorgamiento, devengo, pago, mora, payoff, reversa"],
     "ref": "H-109 · caso contab-balance-guarda · @event.listens_for(Asiento, 'before_insert')"},
    {"id": "qa-dato-real", "categoria": "Calidad",
     "titulo": "QA profundo: componentes, persistencia y dato real (no sólo la UI)",
     "enunciado": "Se verifica la persistencia real en la DB tras cada mutación, y las altas se prueban contra "
                  "Postgres (incluida la carrera borrar-y-recrear y concurrente), no sólo con SQLite en verde.",
     "motivo": "La UI puede 'verse bien' y la base vacía de los tests esconde colisiones que sólo aparecen "
               "contra dato real (H-097).",
     "aplica": ["Toda feature nueva, especialmente altas/creaciones"],
     "ref": "test_deep_qa.py · hallazgos.md"},
    {"id": "cuatro-ojos", "categoria": "Control interno",
     "titulo": "Cuatro-ojos: separación de funciones en aprobaciones",
     "enunciado": "Quien envía a revisión no puede aprobar. Publicar una línea o aprobar una solicitud exige "
                  "un actor distinto del que la preparó. QUIÉN puede aprobar se define con ROLES y GRUPOS "
                  "(Seguridad → Roles/Grupos), no con overrides por nivel: un usuario aprueba un paso si "
                  "tiene el rol que ese nivel exige, ya sea por su perfil principal o heredado de un grupo "
                  "(rol aprobador de créditos = SUPE, grupo «Créditos — Supervisión»). La MISMA regla de roles "
                  "gobierna las capacidades de las pantallas (diseñar/editar vs. aprobar). Las tareas pendientes "
                  "viven en el Inbox de aprobaciones y se avisan como alertas del sistema (badge en la campana).",
     "motivo": "Control interno básico: reduce fraude y error, y deja rastro de quién hizo qué. Unificar 'quién "
               "aprueba' en un único lugar (roles/grupos) lo hace claro y auditable: para habilitar a alguien se "
               "le asigna el rol o el grupo, no un permiso puntual escondido en la config del workflow (H-150). "
               "La cadena de N niveles es a prueba de concurrencia: un nivel se aprueba UNA sola vez (constraint DB "
               "uq_wf_aprobacion_nivel), así dos aprobadores simultáneos no completan la cadena sin aprobar "
               "los niveles superiores (bypass de N-ojos, H-107).",
     "aplica": ["Workflow de líneas (Configurar Créditos)", "Aprobación de solicitudes", "Inbox de aprobaciones"],
     "ref": "H-107/H-150 · casos cfg-workflow, sol-cuatro-ojos, wf-concurrencia, cuatro-ojos-por-roles · "
            "el nivel del workflow define el ROL que aprueba; roles_de() resuelve si el usuario lo tiene "
            "(perfil + grupos); caps_creditos() y _rol_apto() comparten la misma fuente"},
    {"id": "trazabilidad-temporal", "categoria": "Trazabilidad",
     "titulo": "Todo es trazable en el tiempo: versión reproducible y buscable",
     "enunciado": "Toda operación queda ligada a la versión/config con la que se hizo, y esa versión se "
                  "preserva y se puede buscar y ver. Si un crédito se otorgó con la línea v1, se debe poder "
                  "recuperar cómo estaba armada la v1 (el contrato congela su snapshot y la versión histórica "
                  "no se pisa ni se borra).",
     "motivo": "Auditoría, disputas y reproducibilidad: hay que poder reconstruir exactamente bajo qué reglas "
               "se tomó cada decisión, aunque el producto haya cambiado después.",
     "aplica": ["Snapshot del contrato", "Versionado de líneas (vigencia desde/hasta)", "Historial y diff de versión",
                "Auditoría de cambios del sistema nuevo (quién/IP + antes/después + resultado), H-117"],
     "ref": "snapshot_producto · pp_producto_version · caso cfg-vigencia · auditoria_cambios (H-117, casos auditoria-cambio-*)"},
    {"id": "idempotency-key", "categoria": "Datos / Concurrencia",
     "titulo": "Operaciones idempotentes por clave (evitar duplicados por reintento)",
     "enunciado": "Las operaciones mutantes de alta deben poder recibir una Idempotency-Key: si llega dos veces "
                  "la misma clave (doble clic, retry de red), se devuelve el MISMO resultado en lugar de crear "
                  "un segundo registro. Distinto de la unicidad del número (que ya está resuelta): esto dedup-lica "
                  "la OPERACIÓN, no sólo el identificador.",
     "motivo": "Un reintento del cliente no debe generar dos contratos/solicitudes. La unicidad concurrente "
               "evita ids repetidos, pero no evita dos altas lógicas distintas del mismo pedido.",
     "aplica": ["Alta de línea", "Alta de solicitud", "Originar contrato", "Refinanciar", "Servicing (pago/cobro)"],
     "ref": "IMPLEMENTADO (H-108) — header Idempotency-Key + pp_idempotencia (app/core/idempotency.py) en "
            "originar/refinanciar/actividad/solicitud/otorgar/desembolsar/devengar; front dedup-lica el doble "
            "clic (postIdem) incl. cobros de caja; casos idem-key, idem-transiciones; complementa 'unicidad-concurrente'"},
]


def _tabla(insp, nombre: str) -> dict | None:
    if nombre not in insp.get_table_names():
        return None
    pk = set(insp.get_pk_constraint(nombre).get("constrained_columns") or [])
    fks = insp.get_foreign_keys(nombre)
    fk_map = {}
    for f in fks:
        for col in f["constrained_columns"]:
            fk_map[col] = f["referred_table"]
    cols = []
    for c in insp.get_columns(nombre):
        cols.append({
            "nombre": c["name"], "tipo": str(c["type"]),
            "pk": c["name"] in pk, "fk": fk_map.get(c["name"]),
            "nullable": bool(c.get("nullable", True)),
        })
    return {"nombre": nombre, "columnas": cols,
            "relaciones": [{"columna": col, "haciaTabla": tab} for col, tab in fk_map.items()]}


@router.get("")
def controles_version(request: Request):
    insp = inspect(engine)
    grupos = []
    for titulo, tablas in GRUPOS_TABLA:
        ts = [t for t in (_tabla(insp, n) for n in tablas) if t]
        if ts:
            grupos.append({"titulo": titulo, "tablas": ts})

    # Rutas de la API de los routers del módulo.
    prefijos = ("/api/productos", "/api/contratos", "/api/impuestos", "/api/indices",
                "/api/controles-version", "/api/sistema-calculos", "/api/solicitudes", "/api/feriados",
                "/api/aprobaciones", "/api/workflow")
    rutas = []
    vistos = set()
    for r in request.app.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None) or set()
        if not path.startswith(prefijos):
            continue
        for m in sorted(methods - {"HEAD", "OPTIONS"}):
            key = (m, path)
            if key in vistos:
                continue
            vistos.add(key)
            doc = (getattr(r, "endpoint", None).__doc__ or "").strip().split("\n")[0] if getattr(r, "endpoint", None) else ""
            grupo = next((p.replace("/api/", "") for p in prefijos if path.startswith(p)), "")
            rutas.append({"metodo": m, "path": path, "grupo": grupo, "doc": doc})
    rutas.sort(key=lambda x: (x["grupo"], x["path"], x["metodo"]))

    casos = [{"id": i, "pantalla": p, "titulo": t, "tipo": tp, "ref": rf} for i, p, t, tp, rf in CASOS]
    return {
        "menuNuevo": [{"label": a, "ruta": b, "detalle": c} for a, b, c in MENU_NUEVO],
        "changelog": [{"hito": a, "detalle": b} for a, b in CHANGELOG],
        "grupos": grupos,
        "rutas": rutas,
        "casos": casos,
        "totales": {"tablas": sum(len(g["tablas"]) for g in grupos), "rutas": len(rutas),
                    "casos": len(casos), "casosLive": sum(1 for c in casos if c["tipo"] == "live")},
    }


@router.post("/casos/run")
def correr_casos():
    """Corre los casos 'live' (read-only) contra el sistema en ejecución y devuelve el resultado."""
    from time import perf_counter
    from app.core.database import SessionLocal
    resultados = []
    with SessionLocal() as s:
        for cid, pantalla, titulo, tipo, _ref in CASOS:
            if tipo != "live":
                continue
            t0 = perf_counter()
            try:
                ok, detalle = _run_live(cid, s)
            except Exception as e:  # noqa: BLE001
                ok, detalle = False, f"error: {e}"
            resultados.append({"id": cid, "pantalla": pantalla, "titulo": titulo,
                               "ok": bool(ok), "detalle": detalle,
                               "ms": round((perf_counter() - t0) * 1000, 1)})
    return {"resultados": resultados,
            "resumen": {"total": len(resultados), "ok": sum(1 for r in resultados if r["ok"])}}


# ---------------- Principios de diseño (UI) ----------------
# Convenciones de diseño/UI que se aplican a TODA pantalla nueva. Se van sumando. Cada uno con ejemplo.
PRINCIPIOS_DISENO = [
    {"id": "tabla-unica", "categoria": "Componentes",
     "titulo": "Una sola tabla en todo el sistema (componente DataTable)",
     "enunciado": "Todas las grillas usan el componente `DataTable` y se ven IGUALES en todo el sistema, "
                  "salvo aclaración explícita. El modelo de referencia es el Maestro de clientes. **Con candado**: "
                  "check-diseno.mjs (+ hook) falla si una página nueva usa una `<table>` cruda sin DataTable ni "
                  "aclaración 'diseño-ok' / allowlist.",
     "motivo": "Consistencia visual y de interacción: el usuario aprende una sola tabla (orden, paginación, "
               "acciones) y la reconoce en cada pantalla.",
     "ejemplo": "Usuarios y Perfiles se rehicieron con `<DataTable columns cols rows actions clientSort/>` "
                "en vez de una tabla propia, igual que Clientes.",
     "aplica": ["Toda pantalla con listado/grilla"],
     "ref": "src/components/DataTable.tsx · modelo src/pages/Clientes.tsx · candado check-diseno.mjs"},
    {"id": "layout-abm", "categoria": "Layout",
     "titulo": "Layout de ABM: header → card con toolbar → tabla → form de alta/edición",
     "enunciado": "Un ABM se arma con: encabezado (h1 + subtítulo muted + botón '＋ Nuevo'), una card "
                  "(padding 0) con toolbar de búsqueda/filtros (borderBottom) y la DataTable adentro, y "
                  "el alta/edición en un panel/modal de formulario.",
     "motivo": "Estructura predecible: buscar arriba, actuar en la fila, crear/editar en el mismo formulario.",
     "ejemplo": "Maestro de clientes, Usuarios y Perfiles comparten exactamente esta estructura.",
     "aplica": ["Pantallas de alta/baja/modificación"],
     "ref": "src/pages/Clientes.tsx"},
    {"id": "badge-new", "categoria": "Navegación",
     "titulo": "Badge 'new' en opciones nuevas o mejoradas",
     "enunciado": "Las opciones creadas o rehechas en la migración muestran un pill verde `new` a la "
                  "izquierda del nombre en el menú (flag `nuevo: true` en el Sidebar).",
     "motivo": "El usuario distingue de un vistazo lo nuevo de lo legacy.",
     "ejemplo": "Configurar Créditos, Workflow de aprobaciones, Usuarios y Perfiles llevan `nuevo: true`.",
     "aplica": ["Ítems del Sidebar"],
     "ref": "src/components/Sidebar.tsx (nuevo:true → .sb-new)"},
    {"id": "estados-pill", "categoria": "Semántica visual",
     "titulo": "Estados con pills semánticos (ok / warn / crit / brand)",
     "enunciado": "El estado de una fila (Activo/Baja, Habilitado, Vigente, En mora…) se muestra con un "
                  "pill de color semántico: `ok` verde, `warn` ámbar, `crit` rojo, `brand` azul.",
     "motivo": "El estado se lee de un vistazo por color, no sólo por texto.",
     "ejemplo": "`<span className='pill ok'>Activo</span>` / `pill crit` para Baja o mora.",
     "aplica": ["Columnas de estado en cualquier tabla"],
     "ref": "clases .pill.ok/.warn/.crit/.brand"},
    {"id": "css-scopeado", "categoria": "Robustez",
     "titulo": "CSS scopeado por pantalla (evita colisiones)",
     "enunciado": "Cada pantalla prefija sus clases (.cfgc, .sitc, .wfa, .abmu…) para que sus estilos no "
                  "choquen con los de otra pantalla. **Con candado**: check-diseno.mjs (+ hook) falla si una "
                  "página define una clase genérica bare (.card, .row, .cell…) sin prefijo en su <style>.",
     "motivo": "Un nombre de clase genérico compartido rompe layouts en otra pantalla sin avisar.",
     "ejemplo": "El calendario de feriados se veía deforme porque la celda usaba `.fer`, que también "
                "matcheaba el contenedor de página; se renombró a `.hol` (H-083).",
     "aplica": ["Todo <style> de pantalla"],
     "ref": "H-083 (bug del calendario) · candado check-diseno.mjs"},
    {"id": "theme-aware", "categoria": "Theming",
     "titulo": "Colores por variables de tema (light/dark), nunca hex hardcodeado",
     "enunciado": "Los colores salen de variables (--surface, --ink, --brand-2, --ok/--warn/--crit y sus "
                  "*-soft…), no de hex cromático fijo, para funcionar en tema claro y oscuro. Se permiten "
                  "#fff/#000 (house style para texto sobre brand y sombras). **Con candado mecánico**: el "
                  "check frontend/scripts/check-diseno.mjs (+ hook PostToolUse) falla si una página nueva usa "
                  "hex cromático sin aclaración 'diseño-ok' ni estar en diseno-allow-colores.txt.",
     "motivo": "Un `color:#333` queda invisible o feo en el otro tema; y el color semántico se lee de un vistazo.",
     "ejemplo": "Las pantallas nuevas usan `background:var(--surface); color:var(--ink)` y pills `--ok/--ok-soft`. "
                "Los gráficos/leyendas usan la paleta categórica de tema `--dv-*` (blue/green/amber/orange/red/"
                "purple/teal/slate), con variante light+dark, en vez de hex de serie fijos.",
     "aplica": ["Todo estilo con color", "Paletas de data-viz (usar --dv-*)"],
     "ref": "tokens de tema del sistema (incl. --dv-*) · candado check-diseno.mjs"},
    {"id": "formato-es-ar", "categoria": "Formato",
     "titulo": "Números tabulares y formato es-AR",
     "enunciado": "Los importes usan formato es-AR (`toLocaleString('es-AR')`/`$`) y las columnas numéricas "
                  "la clase `.num` (alineadas a la derecha, cifras tabulares).",
     "motivo": "Los números se comparan mejor alineados y con separador de miles local.",
     "ejemplo": "`<span className='num'>{money(c.saldo)}</span>` con `money` es-AR.",
     "aplica": ["Columnas de montos/cantidades"],
     "ref": "helper money() es-AR"},
    {"id": "confirmar-irreversible", "categoria": "Seguridad de UX",
     "titulo": "Confirmar acciones irreversibles y marcarlas en rojo",
     "enunciado": "Baja, borrado y payoff piden confirmación con el diálogo in-app `confirmar({ danger:true })` "
                  "(botón/acción en rojo); si algo no se puede borrar por estar en uso, se deshabilita con motivo.",
     "motivo": "Evita destrucciones accidentales y comunica el riesgo antes de ejecutar.",
     "ejemplo": "Borrar un perfil en uso queda deshabilitado; dar de baja un usuario pide confirmación.",
     "aplica": ["Acciones destructivas en tablas"],
     "ref": "acciones danger:true / hidden en DataTable · confirmar() de src/ui/dialog"},
    {"id": "dialogos-in-app", "categoria": "Seguridad de UX",
     "titulo": "Nada de diálogos nativos del browser: confirmar / avisar / pedirTexto in-app",
     "enunciado": "No se usan window.confirm / alert / prompt (el cartel gris 'localhost dice…'). En su lugar, "
                  "el módulo único `src/ui/dialog.tsx` expone `confirmar()`, `avisar()` y `pedirTexto()`: modal "
                  "centrado, con el tema de la app, scrim, esquinas redondeadas; Esc cancela, Enter acepta y el "
                  "clic en el fondo cierra. El host `<Dialogos/>` se monta una vez en el root.",
     "motivo": "Los diálogos nativos rompen la identidad visual (no respetan tema ni tipografía), no son "
               "consistentes entre navegadores/OS y bloquean el hilo. El módulo in-app es coherente, accesible "
               "por teclado y da variantes (danger para lo irreversible, error para avisos).",
     "ejemplo": "Originar contrato, dar de baja un cliente, liquidar un lote y reversar una actividad abren el "
                "modal in-app; los errores de API se muestran con avisar({ tipo:'error' }).",
     "aplica": ["Confirmaciones", "Avisos/errores", "Entradas de texto rápidas (motivo, importe, clave)"],
     "ref": "H-152 · src/ui/dialog.tsx · caso dialogos-in-app"},
]


# ---------------- Procesos / mecanismos de calidad ----------------
# Los procesos REPETIBLES que garantizan la calidad de la migración: no son "qué construimos" sino
# "cómo lo garantizamos". Cada uno: id, categoria, titulo, descripcion (qué hace), pasos (cómo),
# donde (archivos/mecanismo), verificacion (cómo se prueba), ref (hallazgo).
PROCESOS = [
    {"id": "candado-diseno", "categoria": "Diseño / Enforcement", "titulo": "Candado mecánico de los principios de diseño",
     "descripcion": "Un hook PostToolUse corre en cada Write/Edit de una página y bloquea la edición si viola un principio de diseño, sin depender de que el desarrollador se acuerde.",
     "pasos": ["Se edita una página en src/pages/*.tsx", "El hook hook-check-diseno.sh corre check-diseno.mjs",
               "Se chequean 3 reglas: tabla única (DataTable), color por variable de tema, CSS scopeado por pantalla",
               "Si viola → exit 2 → Claude Code rechaza la edición y muestra el motivo", "Escape: comentario 'diseño-ok' o allowlist"],
     "donde": "frontend/scripts/check-diseno.mjs + hook-check-diseno.sh + .claude/settings.json (PostToolUse)",
     "verificacion": "Se probó en vivo: una página con <table> cruda o hex fijo devuelve exit 2 y bloquea.",
     "ref": "H-104/H-105/H-106 · caso dis-candado"},
    {"id": "qa-profundo", "categoria": "QA", "titulo": "QA profundo: persistencia real y altas contra Postgres",
     "descripcion": "No alcanza con que la API responda: cada mutación se verifica en la DB real, y las altas se prueban contra Postgres (no sólo SQLite en verde), incluida la carrera concurrente.",
     "pasos": ["Ejercer el endpoint (curl/UI)", "Verificar la fila persistida en Postgres (psql)",
               "Probar casos borde y validaciones", "Todo bug encontrado → caso en Controles de Versión + entrada en salida/hallazgos.md",
               "Limpiar los datos demo tras mutar producción"],
     "donde": "salida/hallazgos.md (log vivo) + CASOS (auto/live/manual) + memoria qa-profundo-siempre",
     "verificacion": "Aplicado en cada tanda: IAM, cuatro-ojos, números de dinero, motor de cálculo.",
     "ref": "CLAUDE.md §QA · H-101/H-104/H-108/H-111"},
    {"id": "unicidad-db", "categoria": "Integridad / Concurrencia", "titulo": "Números únicos con la DB como árbitro",
     "descripcion": "Todo identificador de negocio generado (recibo, OP, contrato, resolución, póliza, turno, versión) se crea con 'primer libre' + reintento sobre SAVEPOINT; la constraint única de la DB frena la carrera de dos usuarios concurrentes.",
     "pasos": ["gen_numero() lee el próximo libre", "construir() arma la entidad dentro de un SAVEPOINT (begin_nested)",
               "flush(): si otro tomó el número, IntegrityError revierte sólo el savepoint", "Se reintenta con número fresco"],
     "donde": "app/core/numbering.py (crear_con_numero_unico) + constraints únicas en los modelos",
     "verificacion": "test_caja_concurrencia / test_iam_rol_codigo_unico: la 2ª inserción del mismo número la rechaza la DB.",
     "ref": "H-108 · casos caja-recibo-unico, op-numero-unico, num-compuesto-unico"},
    {"id": "idempotencia", "categoria": "Integridad / Concurrencia", "titulo": "Idempotency-Key en altas y transiciones de dinero",
     "descripcion": "Un reintento o doble-click con la misma Idempotency-Key no duplica la operación: el backend guarda la respuesta y la reproduce; el front deduplica los envíos en vuelo.",
     "pasos": ["El front manda Idempotency-Key (postIdem) y deduplica el doble-click en vuelo",
               "con_idempotencia reserva la clave (PK única) y, si ya existía, reproduce la respuesta guardada",
               "Aplicado a originar/refinanciar/actividad/solicitud/otorgar/desembolsar/devengar + cobros de caja"],
     "donde": "app/core/idempotency.py (con_idempotencia) + postIdem en frontend/src/api.ts",
     "verificacion": "test_idempotencia_transiciones: misma key = misma solicitud/crédito; sin key = nueva.",
     "ref": "H-108 · caso idem-transiciones"},
    {"id": "contab-balanceada", "categoria": "Integridad / Contabilidad", "titulo": "Guarda de contabilidad balanceada (Σdebe = Σhaber)",
     "descripcion": "Un evento before_insert rechaza cualquier asiento de la app (doble partida) que no balancee; los migrados del mayor plano de VFP (una pierna) se excluyen. El invariante falla ruidoso, no en silencio.",
     "pasos": ["Se construye un asiento de la app (origen != 'legacy')", "before_insert suma debe y haber de sus líneas",
               "Si Σdebe ≠ Σhaber → ValueError, no se persiste"],
     "donde": "app/models.py (@event.listens_for(Asiento, 'before_insert'))",
     "verificacion": "test_contabilidad_balance: app desbalanceado → rechazado; legacy de una pierna → permitido.",
     "ref": "H-109 · caso contab-balance-guarda"},
    {"id": "event-sourcing", "categoria": "Integridad / Servicing", "titulo": "Event-sourcing: reversa única + recompute determinista",
     "descripcion": "El servicing es event-sourced: pp_actividad es la verdad y _recompute reconstruye el estado. Una actividad se reversa UNA sola vez (constraint DB) y recomputar N veces da el mismo estado.",
     "pasos": ["_recompute resetea las cuotas al cronograma pristino del snapshot y re-aplica las actividades no-reversadas",
               "Reversar marca REVERSADA + contra-asiento + recompute", "La constraint uq_pp_actividad_reversa_de frena la doble-reversa concurrente"],
     "donde": "app/api/contratos.py (_recompute, reversar) + constraint reversa_de",
     "verificacion": "test_servicing_concurrencia: la DB rechaza la 2ª reversa; recompute 3× = mismo estado.",
     "ref": "H-110 · casos reversa-idempotente, recompute-determinista"},
    {"id": "equivalencia-vfp", "categoria": "Calidad / Cálculo", "titulo": "Equivalencia del motor vs la data real de VFP",
     "descripcion": "El motor de cálculo se verifica reproduciendo AL CENTAVO las cuotas reales migradas de VFP (la fuente de verdad), no sólo con casos sintéticos. Así se detectan errores de fórmula o de mapeo.",
     "pasos": ["Tomar créditos reales migrados de Postgres", "Recomputar su cronograma con el motor usando el tipo_calculo de la línea",
               "Comparar cuota por cuota (amortización, interés, IVA) con la data VFP", "Toda diferencia = un bug de cálculo real"],
     "donde": "tests/test_equivalencia_tipo_calculo.py + fixtures de créditos reales",
     "verificacion": "Encontró y corrigió el mapeo tipo_calculo (VFP 1=Directo, 2/3=Francés) que estaba mal ruteado.",
     "ref": "H-111 · caso equiv-tipo-calculo"},
    {"id": "migrador-traduce", "categoria": "Migración", "titulo": "Migrador que traduce VFP→app y verifica la data antes de tocar",
     "descripcion": "Al migrar un DBF: siempre migrador + modelo + DER + usos en el menú. Los códigos de VFP se TRADUCEN a la convención de la app cuando difieren, y antes de agregar una constraint se verifica que la data migrada no tenga duplicados a ese alcance.",
     "pasos": ["Leer el DBF y mapear al modelo", "Traducir códigos si la semántica difiere (ej. tipo_calcu VFP→app)",
               "Antes de una constraint: verificar duplicados existentes y el ALCANCE real del número",
               "Registrar el migrador en USOS_MENU y sumar su caso/hallazgo"],
     "donde": "app/etl/*.py + memoria migradores-regla + backup-es-produccion-viva",
     "verificacion": "La verificación previa evitó romper la migración en nop/turno (no-únicos por diseño) y fijó tipo_calculo.",
     "ref": "H-108/H-111 · memoria migradores-regla"},
    {"id": "seg-arranque", "categoria": "Seguridad", "titulo": "La app no arranca insegura en producción",
     "descripcion": "Un validador de config impide arrancar en producción con el JWT_SECRET default del código (que es público y permitiría forjar tokens). El secreto se exige por entorno.",
     "pasos": ["Al construir Settings, si environment no es development/test y jwt_secret sigue siendo el default → ValueError",
               "En dev/test se permite el default por comodidad"],
     "donde": "app/core/config.py (model_validator)",
     "verificacion": "test_config_seguridad: producción + default → no arranca; producción + secreto propio → OK.",
     "ref": "H-112 · caso seg-jwt-secret"},
    {"id": "casos-runner", "categoria": "Trazabilidad", "titulo": "Catálogo de casos ejecutable (Controles de Versión)",
     "descripcion": "Cada comportamiento verificado queda registrado como un CASO (auto = test pytest, live = corrible, manual = documentado en UI). El botón 'Correr casos' ejecuta los auto y muestra el tablero verde/rojo.",
     "pasos": ["Al cerrar un bug o feature, se suma su caso con su referencia de test", "POST /casos/run corre los auto",
               "El tablero muestra el estado de cada caso, agrupado por pantalla"],
     "donde": "app/api/controles_version.py (CASOS + /casos/run) + pantalla Controles de Versión",
     "verificacion": "El catálogo tiene 130+ casos; los auto se corren desde la app.",
     "ref": "Controles de Versión (pantalla principal)"},
    {"id": "auditoria-cambios", "categoria": "Trazabilidad / Seguridad", "titulo": "Auditoría de cambios con antes/después + IP",
     "descripcion": "Las mutaciones sensibles del sistema nuevo dejan un rastro rico: quién, desde qué IP, con el estado ANTES y DESPUÉS y el resultado (OK/RECHAZADO/ERROR). Cubre alta de solicitud, originación, pago/prepago/payoff de contrato, cobranza y anulación de recibo, aprobación y rechazo de workflow, y baja de crédito. El registro nunca interrumpe el negocio (falla en silencio ante error propio). Distinto del log VFP migrado, que sólo guarda el hecho. Idea incorporada del memo de migración de créditos.",
     "pasos": ["El endpoint captura el actor (usuario/perfil por token, IP por X-Forwarded-For)",
               "Tras la mutación registra entidad, operación, resultado y el diff antes/después",
               "Los rechazos de regla o validación también se auditan (resultado RECHAZADO/ERROR)",
               "Seguridad → Auditoría de cambios lista y filtra el rastro (por operación/resultado); el diff se ve por evento"],
     "donde": "app/services/auditoria.py (registrar_cambio/_diff) · app/deps.py (get_actor) · creditos.py/contratos.py/caja.py/aprobaciones.py · admin.py (/auditoria-cambios) · pantalla Seguridad → Auditoría de cambios",
     "verificacion": "test_auditoria_cambios: una alta/pago OK deja rastro con IP y datos_nuevos; un rechazo deja resultado RECHAZADO/ERROR.",
     "ref": "H-117/H-118 · casos auditoria-cambio-alta / auditoria-cambio-rechazo / auditoria-cambio-pago-aprobacion"},
]


@router.get("/procesos")
def procesos():
    """Procesos/mecanismos de calidad que garantizan la migración (candado, guardas, equivalencia, QA…)."""
    return {"items": PROCESOS, "total": len(PROCESOS)}


@router.get("/principios")
def principios():
    """Principios de arquitectura que guían las decisiones de diseño de la app (se van sumando)."""
    return {"items": PRINCIPIOS, "total": len(PRINCIPIOS)}


@router.get("/principios-diseno")
def principios_diseno():
    """Principios de diseño/UI que se aplican a toda pantalla nueva (se van sumando)."""
    return {"items": PRINCIPIOS_DISENO, "total": len(PRINCIPIOS_DISENO)}
