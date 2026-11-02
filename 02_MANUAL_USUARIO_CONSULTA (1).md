# Manual de usuario — Rol Consulta

**Sistema de Inventario y Seguridad de Red — Municipalidad Distrital de Alto Selva Alegre**
Versión 1.0 · Octubre de 2026

---

## 1. A quién va dirigido

A cualquier persona autorizada que necesite **consultar** información de la red: qué equipos existen, dónde están, qué VLAN y subredes hay y cuándo toca el mantenimiento. Con este rol **no se puede modificar nada**.

| Con rol Consulta puedo… | No puedo… |
|---|---|
| Ver equipos, VLAN, subredes y mantenimientos | Crear, editar ni borrar datos |
| Cambiar mi propia contraseña | Ver la lista de usuarios ni sus contraseñas |
| Exportar lo que veo a Excel (CSV) | Programar mantenimientos (eso es del rol Técnico) |

Si necesita más permisos, pídalos al administrador del sistema: [completar nombre y contacto].

## 2. Antes de empezar

Necesita cuatro datos, que le entrega el administrador:

| Dato | Ejemplo |
|---|---|
| Dirección del servidor | `https://red.altoselvaalegre.gob.pe` (o `http://servidor:3000` en pruebas) |
| Su correo | `su.nombre@dominio.pe` |
| Su contraseña inicial (temporal) | Se cambia en el primer ingreso (sección 4) |
| La carpeta del sistema en su equipo | `C:\proyecto_red` |

## 3. Preparar la consola (solo la primera vez)

1. Instale **PowerShell 7** (si no lo tiene): abra el menú Inicio, busque *Símbolo del sistema*, y escriba
   `winget install Microsoft.PowerShell`. Luego abra **PowerShell 7** desde el menú Inicio.
2. Cargue las herramientas del sistema:
   ```powershell
   Import-Module C:\proyecto_red\scripts\RedCli.psm1 -Force
   ```
3. Compruebe que están disponibles:
   ```powershell
   Get-Command -Module RedCli
   ```
   Debe ver una lista que incluye `Connect-Red`, `Get-RedDispositivo` y `Get-RedSubred`.

> **Si Windows muestra «la ejecución de scripts está deshabilitada»**, ejecute una sola vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y confirme con `S`.
>
> **Cada vez que abra una ventana nueva** de PowerShell, repita el paso 2.

## 4. Iniciar sesión

```powershell
Connect-Red -Url http://servidor:3000 -Correo su.nombre@dominio.pe
```

El sistema pide la contraseña (al escribirla **no se muestra nada**; es normal). Si es correcta verá:

```
Id                                   Rol      Servidor
--                                   ---      --------
e03a2c3e-e06d-4735-847c-ed7a1528b9b4 consulta http://servidor:3000
```

La columna **Rol** debe decir `consulta`. A partir de aquí puede usar los comandos de la sección 5.

**Primer ingreso:** cambie de inmediato la contraseña temporal (sección 5.10).

**Si no puede entrar:**

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| *Correo o contraseña incorrectos…* | Algún dato está mal, o la cuenta está desactivada o bloqueada | Revise mayúsculas y el teclado. Con 5 errores seguidos la cuenta se bloquea **15 minutos**; espere o pida al administrador que la restablezca |
| *No se pudo contactar con el servidor…* | La dirección es incorrecta o el sistema está apagado | Verifique la dirección con el administrador |
| *Demasiados intentos…* | Se superó el límite de intentos | Espere unos minutos |

## 5. Qué puedo consultar

### 5.1 Saber quién soy
```powershell
Get-RedYo
```
Muestra su identificador y su rol.

### 5.2 Ver los equipos (dispositivos)
Todos los equipos:
```powershell
Get-RedDispositivo | Format-Table Nombre, Tipo, Estado, Piso -AutoSize
```
Solo los de un tipo (por ejemplo, servidores):
```powershell
Get-RedDispositivo -Tipo servidor | Format-Table Nombre, Tipo, Estado, Piso -AutoSize
```
```
Nombre     Tipo     Estado    Piso
------     ----     ------    ----
SRV-ADM-1  servidor operativo    4
SRV-ADM-2  servidor operativo    4
SRV-ARCH-1 servidor operativo    4
SRV-GOB-1  servidor operativo    4
SRV-GOB-2  servidor operativo    4
SRV-GOB-3  servidor operativo    4
```
Los **tipos** disponibles son: `firewall`, `router`, `switch`, `access_point`, `servidor`, `ups`, `onu`, `radioenlace`, `modem` y `otro`.

Solo los que tienen un estado determinado:
```powershell
Get-RedDispositivo -Estado averiado
```
Los **estados** son: `operativo`, `en_mantenimiento`, `averiado`, `retirado` y `propuesto` (equipo planificado, aún no instalado).

Buscar por parte del nombre:
```powershell
Get-RedDispositivo -Nombre FW
```

### 5.3 Ver el detalle de un equipo y dónde está
```powershell
Get-RedDispositivo -Nombre FW | Format-List Nombre, Tipo, Marca, Modelo, Estado, Sede, Piso, Ambiente
```
```
Nombre   : FW-FORTIGATE-90G
Tipo     : firewall
Marca    : Fortinet
Modelo   : FortiGate 90G
Estado   : operativo
Sede     : Municipalidad (edificio principal)
Piso     : 4
Ambiente : Centro de datos / área de redes
```
Para ver **todas las observaciones y sus interfaces (IP y MAC)** use su identificador (columna `Id`):
```powershell
$equipo = Get-RedDispositivo -Nombre FW-FORTIGATE
Get-RedDispositivo -Id $equipo.Id
```

### 5.4 Ver las VLAN
```powershell
Get-RedVlan | Format-Table -AutoSize
```
```
Numero Nombre    Funcion                  Diseno
------ ------    -------                  ------
    10 SERVERS   Red de servidores        propuesto
    20 PRINTERS  Red de impresoras        propuesto
    30 AREA_X    Usuarios (Pisos 1 y 3)   propuesto
    40 AREA_Y    Usuarios (Pisos 2 y 4)   propuesto
    50 SEGURIDAD Enlace con Seguridad ... propuesto
    99 MGMT      Administración/switches  propuesto
```
**Diseño `actual`** = existe hoy. **`propuesto`** = forma parte del rediseño TO-BE del Diario de Ingeniería. Hoy la red es plana (sin VLAN), por eso todas figuran como propuestas.

### 5.5 Ver las subredes y su ocupación
```powershell
Get-RedSubred | Format-Table -AutoSize
```
```
Red           Diseno    Funcion                                                     Capacidad IPRegistradas
---           ------    -------                                                     --------- -------------
10.0.0.0/24   actual    Edificio central: servidores centrales (SIAF, Intranet, BD)       254             0
10.0.1.0/24   actual    Edificio derecho: PCs e impresoras administrativas                254             0
10.0.2.0/24   actual    Roosevelt: oficinas remotas por radioenlace                       254             0
10.10.10.0/24 propuesto Servidores (máscara /24 supuesta)                                 254             0
...
```
- **Capacidad**: cuántos equipos admite la subred (una `/24` admite 254).
- **IPRegistradas**: cuántas IP están anotadas en el sistema. Si es menor que las que realmente se usan, el inventario está incompleto.
- Si «IPRegistradas» se acerca a «Capacidad», la subred se está quedando corta.

### 5.6 Ver los mantenimientos
Todos los mantenimientos registrados:
```powershell
Get-RedMantenimiento | Format-Table Dispositivo, Tipo, Estado, Programada, Realizada -AutoSize
```
Los **próximos a vencer** (según la periodicidad de cada equipo):
```powershell
Get-RedMantenimiento -Proximos | Format-Table -AutoSize
```
> Si esta lista aparece **vacía**, no es un error: se llena cuando un equipo tiene fecha de instalación o un mantenimiento completado. Avise al administrador si falta información.

### 5.7 Filtrar y ordenar lo que veo
Los resultados se pueden combinar con las órdenes habituales de PowerShell:
```powershell
# Equipos del piso 4, ordenados por nombre
Get-RedDispositivo | Where-Object Piso -eq 4 | Sort-Object Nombre | Format-Table Nombre, Tipo, Estado

# Mantenimientos aún pendientes, del más cercano al más lejano
Get-RedMantenimiento | Where-Object Estado -in 'programado','en_curso' | Sort-Object Programada | Format-Table
```

### 5.8 Llevar la información a Excel
```powershell
Get-RedDispositivo | Export-Csv C:\Temp\dispositivos.csv -NoTypeInformation -Encoding UTF8
```
Abra el archivo con Excel (*Datos → Desde texto/CSV*, codificación UTF-8, para que se vean las tildes). Trate el archivo como información de uso interno: **no lo envíe por canales públicos ni lo deje en equipos compartidos**.

### 5.9 Ver más información de un comando
```powershell
Get-Help Get-RedDispositivo -Examples
```

### 5.10 Cambiar mi contraseña
```powershell
Set-RedContrasena
```
Pide la contraseña actual y la nueva (sin mostrarlas). Al terminar **se cierran todas sus sesiones** y debe volver a conectarse con `Connect-Red`.

Requisitos de la contraseña nueva: **12 o más caracteres**, con **mayúscula, minúscula, número y símbolo**.
Ejemplo de cómo construir una buena: piense en una frase y conviértala, como «Mi hijo nació en Arequipa en 2015» → `Mh-nacio-en-AQP-2015!`. No use esta, cree la suya.

### 5.11 Cerrar sesión
```powershell
Disconnect-Red
```
Hágalo siempre al terminar, especialmente si el equipo lo usan otras personas. La sesión además se cierra sola tras 30 minutos sin actividad.

## 6. Qué significan los datos

| Campo | Significado |
|---|---|
| `Nombre` | Nombre único del equipo (por ejemplo `SRV-GOB-1`, `SW-TPLINK-SG3428MP`) |
| `Tipo` | Clase de equipo (firewall, switch, servidor…) |
| `Estado` | Situación del equipo (operativo, averiado…) |
| `Sede`, `Piso`, `Ambiente` | Dónde está físicamente |
| `Diseno` | `actual` (existe hoy) o `propuesto` (rediseño) |
| `Tipo` de mantenimiento | `preventivo` (planificado), `correctivo` (por falla), `inspeccion` (revisión) |
| `Estado` de mantenimiento | `programado`, `en_curso`, `completado`, `cancelado` |
| `Programada` / `Realizada` | Fechas en formato AAAA-MM-DD (año-mes-día) |

## 7. Mensajes que puede ver

| Mensaje | Qué hacer |
|---|---|
| *No hay sesión activa…* | Ejecute `Connect-Red` |
| *La sesión no es válida o caducó…* | Pasaron 30 minutos sin actividad o la contraseña cambió: ejecute `Connect-Red` otra vez |
| *Su rol no permite esta acción…* | Esa operación requiere otro rol; consulte al administrador |
| *No se encontró el registro, o su rol no puede verlo* | Revise el nombre o el identificador |
| *Datos no válidos…* | Revise lo que escribió (por ejemplo, un tipo que no existe) |
| *No se pudo contactar con el servidor…* | El sistema no responde; avise al administrador |
| *The term 'Connect-Red' is not recognized…* | No cargó las herramientas: repita el paso 2 de la sección 3 |



| Necesidad | Contacto |
|---|---|
| Acceso, contraseña o permisos | Administrador del sistema: [completar] |
| Incidente de seguridad | Responsable de seguridad: [completar] |
| El sistema no responde | Soporte técnico: [completar] |
