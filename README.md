# PresupACL

Sistema web local para elaborar cotizaciones de seguridad electrónica para **ACL Alarmas y Cámaras de León**.

Equipo **SofChi**: Sofía Quesada y Vanesa Estrada · Desarrollo de Aplicaciones y Servicios Virtuales · Universidad Iberoamericana León · Prof. Ing. Alejandro Montes Moreno.

## Estado

Incremento 1 (RF-02 · registrar cliente con nombre, teléfono y una o varias direcciones), según el plan de implementación v1.1 del 29-oct-2026.

| Tarea | Módulo | Estado |
|---|---|---|
| T-01 Estructura base y repositorio | proyecto | Terminada |
| T-03 Esquema SQLite con FK | almacenamiento_datos | Terminada (P11) |
| T-04 Guardado transaccional y consulta | almacenamiento_datos | Terminada (CA-04, CA-38, P01, P12, P13) |
| T-02 / T-05 Contrato y validación | clientes_registro | Pendiente (módulo 2) |
| T-06 Integración y P01 | ambos | Pendiente |

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

## Estructura

```
proyecto/
  infraestructura/   almacenamiento_datos.py (único módulo que accede a la BD)
  tests/             test_<modulo>.py por cada módulo
data/                presupacl.db (se crea al ejecutar; no se sube al repositorio)
```

Las demás carpetas de la arquitectura (auth, clientes, catalogo, cotizaciones, etc.) se agregan cuando su incremento tenga código.

## Reglas del repositorio

- No se suben bases de datos, archivos `.env`, credenciales ni logs.
- Cada commit de código lleva su push y se verifica en GitHub.
- Las pruebas usan datos ficticios y una base temporal.
