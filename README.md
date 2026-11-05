# PresupACL

Sistema web local para elaborar cotizaciones de seguridad electrónica para **ACL Alarmas y Cámaras de León**.

Equipo **SofChi**: Sofía Quesada y Vanesa Estrada · Desarrollo de Aplicaciones y Servicios Virtuales · Universidad Iberoamericana León · Prof. Ing. Alejandro Montes Moreno.

## Estado

**Incremento 1 terminado (v0.1.0):** RF-02 · registrar cliente con nombre, teléfono y una o varias direcciones, según el plan de implementación v1.2.

| Tarea | Módulo | Estado |
|---|---|---|
| T-01 Estructura base y repositorio | proyecto | Terminada |
| T-02 Contrato de entradas, salidas y errores | clientes_registro | Terminada |
| T-03 Esquema SQLite con FK | almacenamiento_datos | Terminada (P11) |
| T-04 Guardado transaccional y consulta | almacenamiento_datos | Terminada (CA-04, CA-38, P01, P12, P13) |
| T-05 Validación de campos obligatorios | clientes_registro | Terminada (CA-05, CA-68) |
| T-06 Integración, P01 y demostración | ambos | Terminada (PT-02-N/L/E/E2, P01) |

Documentos vigentes en `docs/`: especificación v2.5 y plan de implementación v1.2. El plan de los siguientes incrementos vivirá en `docs/plan_incrementos.md`.

## Requisitos

- Python 3.10 o superior (se usa `sqlite3` de la biblioteca estándar).
- pytest para las pruebas.

```bash
python -m pip install -r requirements.txt
```

## Ejecutar pruebas

Desde la raíz del repositorio:

```bash
python -m pytest -v
```

## Demostración del incremento 1

```bash
python -m proyecto.demo_rf02
```

Crea `data/presupacl.db`, registra un cliente ficticio con dos direcciones, lo vuelve a leer y muestra un registro rechazado por datos faltantes. Para ver la BD en VS Code se puede usar la extensión "SQLite Viewer".

## Estructura

```
proyecto/
  clientes/          clientes_registro.py (validación y registro de clientes)
  infraestructura/   almacenamiento_datos.py (único módulo que accede a la BD)
  tests/             test_<modulo>.py por módulo y pruebas de integración
  demo_rf02.py       demostración por consola del incremento 1
docs/                especificación y planes aprobados
data/                presupacl.db (se crea al ejecutar; no se sube al repositorio)
```

Las demás carpetas de la arquitectura (auth, catalogo, cotizaciones, etc.) se agregan cuando su incremento tenga código.

## Reglas del repositorio

- No se suben bases de datos, archivos `.env`, credenciales ni logs.
- Cada commit de código lleva su push y se verifica en GitHub.
- Las pruebas usan datos ficticios y una base temporal.
