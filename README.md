# Sistema de Inventario y Seguridad de Red — Municipalidad Distrital de Alto Selva Alegre

**Versión:** 1.0  
**Entidad:** Municipalidad Distrital de Alto Selva Alegre (Arequipa, Perú)  


## 1. Resumen Ejecutivo

El **Sistema de Inventario y Seguridad de Red** es una solución de software orientada a la gestión centralizada de la infraestructura de telecomunicaciones y al modelado de directivas de seguridad perimetral para la Municipalidad Distrital de Alto Selva Alegre.

El proyecto surge como resultado técnico y académico del *Diario de Ingeniería – Visita Académica a la Municipalidad de Alto Selva Alegre* y de las prácticas de simulación sobre Listas de Control de Acceso (ACL) y traducción de direcciones de red (NAT/PAT) ejecutadas en entornos Cisco.

La plataforma integra un catálogo relacional normalizado de activos de red, un subsistema de calendarización y trazabilidad de mantenimientos preventivos y correctivos, y herramientas de validación lógica de seguridad perimetral, garantizando el cumplimiento de los pilares de la seguridad de la información: **Confidencialidad, Integridad y Disponibilidad**.

## 2. Objetivos del Proyecto

### 2.1. Objetivo General

Diseñar e implementar una plataforma integral de catálogo, trazabilidad y evaluación de directivas de seguridad para la infraestructura de red de la Municipalidad Distrital de Alto Selva Alegre, soportada en un modelo de control de acceso basado en roles (RBAC) y mecanismos de auditoría inmutable a nivel de motor de base de datos.

### 2.2. Objetivos Específicos

- **Consolidación del Catálogo de Activos:** Estructurar el inventario físico y lógico de equipos de red (firewalls, routers, switches, servidores, radioenlaces, ONUs y UPS) en una base de datos relacional estandarizada.
- **Trazabilidad de Mantenimientos:** Proveer un algoritmo de cálculo dinámico para el seguimiento, vencimiento y ejecución de mantenimientos preventivos y correctivos por activo.
- **Rediseño Arquitectural (AS-IS / TO-BE):** Mapear la transición desde la topología plana actual hacia una arquitectura segmentada mediante Redes de Área Local Virtuales (VLANs 10, 20, 30, 40, 50 y 99).
- **Simulación y Verificación de ACLs:** Validar sintáctica y lógicamente las reglas de filtrado de paquetes previa a su implementación física en los equipos de ruteo de producción.
- **Seguridad y Auditoría:** Garantizar el no repudio y la inmutabilidad de los registros mediante *triggers* transaccionales y aislamiento por *Row Level Security* (RLS).

## 3. Arquitectura del Sistema

El sistema implementa un modelo de tres capas (*3-Tier Architecture*) desacopladas para garantizar el aislamiento de responsabilidades, la integridad transaccional y la seguridad de la información.

```text
┌────────────────────────────────────────────────────────┐
│             Capa de Presentación (CLI)                 │
│                  PowerShell 7 (RedCli)                  │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ HTTPS / REST (JSON)
                            ▼
┌────────────────────────────────────────────────────────┐
│             Capa de Negocio (API REST)                 │
│              Node.js 20+ / Express.js / Zod             │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ SQL / TLS (App User Session)
                            ▼
┌────────────────────────────────────────────────────────┐
│         Capa de Persistencia y Seguridad (BD)          │
│       PostgreSQL 16 / Esquema 'infra' / RLS             │
└────────────────────────────────────────────────────────┘
```

### 3.1. Descripción de las Capas

1. **Capa de Presentación (CLI):** Consola cliente implementada en PowerShell 7 (`RedCli.psm1`) que encapsula la lógica de comunicación HTTP/HTTPS, el enmascaramiento de entradas y la gestión segura de tokens y sesiones en memoria.

2. **Capa de Negocio (API REST):** Servicio backend desarrollado en Node.js y Express.js responsable de la validación estricta de esquemas (mediante Zod), control de tasa de peticiones (*rate limiting* de dos capas), mitigación de vulnerabilidades OWASP (Helmet, CSRF Tokens de doble envío) y manejo de estados de sesión.

3. **Capa de Persistencia (Base de Datos):** Servidor PostgreSQL 16 configurado bajo el esquema aislado `infra`. Aplica políticas de *Row Level Security* (RLS) y funciones encapsuladas en `SECURITY DEFINER` para evitar la elusión de privilegios a nivel de aplicación.

## 4. Especificaciones Técnicas

| **Componente** | **Tecnología / Estándar** | **Propósito en el Sistema** |
|---|---|---|
| Motor de Base de Datos | PostgreSQL 16 | Almacenamiento relacional con tipos nativos CIDR/INET, validaciones CHECK y auditoría inmutable. |
| Servicio Backend | Node.js 20+ / Express.js | API RESTful orientada al procesamiento de lógica de negocio y mediación con la base de datos. |
| Validación de Datos | Zod 3.x | Tipado estricto y sanitización contra inyecciones y cargas útiles no deseadas. |
| Consola Operativa | PowerShell 7.x | Interfaz de comandos modular (`RedCli.psm1`) para roles de consulta y soporte técnico. |
| Cifrado de Credenciales | Bcrypt (Cost Factor 12) | Derivación criptográfica irreversible de contraseñas de usuario. |
| Simulación de Red | Cisco Packet Tracer | Entorno de validación topológica y pruebas de ruteo y conmutación. |

## 5. Estructura del Repositorio

```text
proyecto_red/
├── api/                              # Capa de Negocio / API RESTful (Node.js)
│   ├── package.json
│   ├── server.js                     # Implementación de endpoints y seguridad HTTP
│   └── .env.example                  # Plantilla de variables de entorno
│
├── bd/                               # Definición de Esquema y Scripts SQL
│   ├── infra_red_schema_seguro.sql   # DDL, DML, políticas RLS y Triggers
│   └── diccionario_datos.sql         # Extracción automatizada del catálogo de datos
│
├── docs/                             # Documentación Técnica e Histórica
│   ├── 01_INFORMACION_DEL_SISTEMA.md # Especificación funcional del sistema
│   ├── 02_MANUAL_USUARIO_CONSULTA.md # Guía operativa: Rol Consulta
│   ├── 03_MANUAL_USUARIO_TECNICO.md  # Guía operativa: Rol Técnico
│   ├── 06_DICCIONARIO_DE_DATOS.md    # Estructura detallada de entidades
│   └── guia_seguridad.md             # Matriz de riesgos y controles de seguridad
│
└── scripts/                          # Cliente de Consola (CLI)
    └── RedCli.psm1                   # Módulo cliente para PowerShell 7
```

## 6. Procedimiento de Despliegue e Instalación

### 6.1. Requisitos Previos

- Entorno de ejecución **Node.js** v20.0.0 o superior instalado.
- Instancia activa del motor de base de datos **PostgreSQL 16**.
- Consola **PowerShell 7** (`pwsh`) para la ejecución del cliente operativo.

### 6.2. Despliegue de la Base de Datos

Ejecutar los siguientes comandos para crear la base de datos e inicializar la estructura, tipos enumerados y políticas de seguridad:

```bash
createdb -U postgres infra_red_db

psql -U postgres -d infra_red_db -f bd/infra_red_schema_seguro.sql
```

### 6.3. Despliegue del Servicio Backend (API REST)

**1.** Navegar al directorio de la API e instalar las dependencias requeridas:

```bash
cd api
npm install
```

**2.** Configurar las variables de entorno creando un archivo `.env`:

```ini
DATABASE_URL=postgres://app_backend:clave_segura@127.0.0.1:5432/infra_red_db
NODE_ENV=production
PORT=3000
ALLOWED_ORIGINS=https://red.altoselvaalegre.gob.pe
```

**3.** Iniciar el servicio:

```bash
npm start
```

### 6.4. Inicialización de la Consola Cliente (CLI)

**1.** Abrir una sesión de PowerShell 7 e importar el módulo de gestión:

```powershell
Import-Module C:\proyecto_red\scripts\RedCli.psm1 -Force
```

**2.** Autenticar la sesión de usuario mediante credenciales institucionales:

```powershell
Connect-Red -Url http://127.0.0.1:3000 -Correo usuario@altoselvaalegre.gob.pe
```

## 7. Modelo de Seguridad y Matriz de Permisos (RBAC)

El control de acceso se rige estrictamente por un modelo basado en roles parametrizado en la base de datos.

| **Rol de Usuario** | **Permisos sobre Inventario** | **Permisos sobre Mantenimientos** | **Gestión de Usuarios y ACLs** |
|---|---|---|---|
| `consulta` | Lectura (`SELECT`) | Lectura (`SELECT`) | Sin acceso |
| `tecnico` | Lectura (`SELECT`) | Lectura y registro/actualización de asignaciones propias | Sin acceso |
| `administrador` | Lectura, escritura y modificación | Control total de órdenes | Alta, baja, cambio de roles y gestión de ACLs |

## 8. Licencia y Uso Institucional

Este software y su documentación asociada se distribuyen bajo la licencia **MIT**.

Desarrollado con fines académicos y como propuesta de modernización tecnológica para la infraestructura de red de la Municipalidad Distrital de Alto Selva Alegre.
