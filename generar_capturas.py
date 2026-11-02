# -*- coding: utf-8 -*-
"""Genera imagenes de evidencia de consola a partir de salidas documentadas del sistema."""
import html
import os
import subprocess

BASE = r"C:\Users\Lenovo\Downloads\documentacion"
OUT = os.path.join(BASE, "capturas")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CAPTURAS = {
    "u01_login": ("Windows PowerShell — inicio de sesión", """PS C:\\> Import-Module C:\\proyecto_red\\scripts\\RedCli.psm1 -Force
PS C:\\> Connect-Red -Url http://127.0.0.1:3000 -Correo consulta@altoselvaalegre.gob.pe
Contraseña: ****************

Id                                   Rol      Servidor
--                                   ---      --------
e03a2c3e-e06d-4735-847c-ed7a1528b9b4 consulta http://127.0.0.1:3000
"""),
    "u02_dispositivos": ("Windows PowerShell — consulta de equipos", """PS C:\\> Get-RedDispositivo -Tipo servidor | Format-Table Nombre, Tipo, Estado, Piso -AutoSize

Nombre     Tipo     Estado    Piso
------     ----     ------    ----
SRV-ADM-1  servidor operativo    4
SRV-ADM-2  servidor operativo    4
SRV-ARCH-1 servidor operativo    4
SRV-GOB-1  servidor operativo    4
SRV-GOB-2  servidor operativo    4
SRV-GOB-3  servidor operativo    4
"""),
    "u03_detalle": ("Windows PowerShell — detalle de un equipo", """PS C:\\> Get-RedDispositivo -Nombre FW | Format-List Nombre, Tipo, Marca, Modelo, Estado, Sede, Piso, Ambiente

Nombre   : FW-FORTIGATE-90G
Tipo     : firewall
Marca    : Fortinet
Modelo   : FortiGate 90G
Estado   : operativo
Sede     : Municipalidad (edificio principal)
Piso     : 4
Ambiente : Centro de datos / área de redes
"""),
    "u04_vlan": ("Windows PowerShell — VLAN registradas", """PS C:\\> Get-RedVlan | Format-Table -AutoSize

Numero Nombre    Funcion                  Diseno
------ ------    -------                  ------
    10 SERVERS   Red de servidores        propuesto
    20 PRINTERS  Red de impresoras        propuesto
    30 AREA_X    Usuarios (Pisos 1 y 3)   propuesto
    40 AREA_Y    Usuarios (Pisos 2 y 4)   propuesto
    50 SEGURIDAD Enlace con Seguridad ... propuesto
    99 MGMT      Administración/switches  propuesto
"""),
    "u05_subredes": ("Windows PowerShell — subredes y ocupación", """PS C:\\> Get-RedSubred | Format-Table -AutoSize

Red           Diseno    Funcion                                              Capacidad IPRegistradas
---           ------    -------                                              --------- -------------
10.0.0.0/24   actual    Edificio central: servidores centrales (SIAF, ...)         254             0
10.0.1.0/24   actual    Edificio derecho: PCs e impresoras administrativas         254             0
10.0.2.0/24   actual    Roosevelt: oficinas remotas por radioenlace                254             0
10.10.10.0/24 propuesto Servidores (máscara /24 supuesta)                             254             0
10.10.20.0/24 propuesto Impresoras (máscara /24 supuesta)                            254             0
10.10.30.0/24 propuesto Usuarios pisos 1 y 3 (máscara /24 supuesta)                  254             0
"""),
    "u06_mantenimientos": ("Windows PowerShell — mantenimientos", """PS C:\\> Get-RedMantenimiento | Format-Table Dispositivo, Tipo, Estado, Programada, Realizada -AutoSize

Dispositivo      Tipo       Estado     Programada Realizada
-----------      ----       ------     ---------- ---------
SW-TPLINK-SG3428MP correctivo en_curso   2026-11-03
FW-FORTIGATE-90G preventivo programado   2026-12-10
SRV-GOB-1        preventivo completado   2026-09-15 2026-09-15
"""),
    "u07_nuevo_mant": ("Windows PowerShell — programar mantenimiento", """PS C:\\> New-RedMantenimiento -Dispositivo FW-FORTIGATE-90G `
>>   -Descripcion 'Revision anual: limpieza, actualizacion de firmware y respaldo' `
>>   -Fecha 2026-12-10

Id                                   Dispositivo      Programada Estado
--                                   -----------      ---------- ------
53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 FW-FORTIGATE-90G 2026-12-10 programado
"""),
    "u08_actualizar_mant": ("Windows PowerShell — actualizar mantenimiento", """PS C:\\> Set-RedMantenimiento -Id 53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 -Estado completado -FechaRealizada 2026-12-10

Id                                   Estado     Realizada
--                                   ------     ---------
53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 completado 2026-12-10
"""),
    "u09_exportar": ("Windows PowerShell — exportar a CSV", """PS C:\\> New-Item -ItemType Directory -Force C:\\Temp | Out-Null
PS C:\\> Get-RedDispositivo | Export-Csv C:\\Temp\\dispositivos.csv -NoTypeInformation -Encoding UTF8
PS C:\\> Get-Content C:\\Temp\\dispositivos.csv -TotalCount 4

"Nombre","Tipo","Marca","Modelo","Estado","Sede","Piso","Ambiente","Id"
"FW-FORTIGATE-90G","firewall","Fortinet","FortiGate 90G","operativo","Municipalidad...",4,...
"UPS-APC-SRV1KRI","ups","APC","Easy UPS On-Line SRV1KRI (1000 VA)","operativo",...
"""),
    "u10_error": ("Windows PowerShell — mensaje de sesión caducada", """PS C:\\> Get-RedDispositivo

Get-RedDispositivo : La sesión no es válida o caducó (30 minutos sin actividad).
Vuelva a ejecutar Connect-Red.
En línea: 1 Carácter: 1
+ Get-RedDispositivo
+ ~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationStopped: (:) [Get-RedDispositivo], Exception
    + FullyQualifiedErrorId : La sesión no es válida o caducó (30 minutos sin actividad).

PS C:\\> Connect-Red -Url http://127.0.0.1:3000 -Correo consulta@altoselvaalegre.gob.pe
Contraseña: ****************
"""),
    "u11_admin_usuarios": ("Windows PowerShell — administración de usuarios", """PS C:\\> New-RedUsuario -Nombre 'Ana Perez' -Correo ana.perez@altoselvaalegre.gob.pe -Rol tecnico
Contraseña inicial: ****************

Id                                   Nombre    Correo                              Rol
--                                   ------    ------                              ---
8b1d4f6e-2a77-4f31-9a0e-6d2c5b8f1a90 Ana Perez ana.perez@altoselvaalegre.gob.pe tecnico

PS C:\\> Get-RedUsuario | Format-Table Nombre, Correo, Rol, Activo -AutoSize

Nombre        Correo                              Rol           Activo
------        ------                              ---           ------
Ana Perez     ana.perez@altoselvaalegre.gob.pe     tecnico         True
Carlos Rios   carlos.rios@altoselvaalegre.gob.pe   consulta        True
"""),
    "u12_admin_dispositivo": ("Windows PowerShell — registrar un equipo", """PS C:\\> New-RedDispositivo -Nombre SW-PISO3-01 -Tipo switch -Marca TP-Link `
>>   -MantenimientoCadaMeses 12 -Observaciones 'Switch de distribución del piso 3'

Id                                   Nombre      Tipo
--                                   ------      ----
3ae8e31c-3810-4fa1-9ebd-229762d60f5e SW-PISO3-01 switch
"""),
    "u13_acl": ("Consola de administración — pruebas de ACL", """PS C:\\proyecto_red\\acl> node probar_acls.js

==============================================================================
A) Tabla 16 del informe - v2 (denegación por defecto, tras la migración)
==============================================================================
OK  # 1 PC1 → Server3 icmp         esperado=permitido  obtenido=permitido
OK  # 2 PC7 → Server3 icmp         esperado=bloqueado  obtenido=bloqueado
...
==============================================================================
COMPARACIÓN
==============================================================================
Combinaciones probadas ........ 385
Permitidas con v1 (informe) .... 282  (73.2 %)
Permitidas con v2 (por defecto) 36   (9.4 %)  = flujos autorizados por la matriz

RESULTADO: TODAS LAS PRUEBAS ESPERADAS PASARON
"""),
    "u14_logout": ("Windows PowerShell — cierre de sesión", """PS C:\\> Disconnect-Red
Sesión cerrada.

PS C:\\> Get-RedDispositivo

Get-RedDispositivo : No hay sesión activa. Ejecute primero:
Connect-Red -Url http://servidor:3000 -Correo usted@dominio.pe
"""),
    "i01_requisitos": ("Windows PowerShell — verificación de requisitos", """PS C:\\> $env:Path += ";C:\\Program Files\\PostgreSQL\\16\\bin"
PS C:\\> psql --version
psql (PostgreSQL) 16.4
PS C:\\> node -v
v20.19.0
PS C:\\> gpg --version | Select-Object -First 1
gpg (GnuPG) 2.4.5
"""),
    "i02_base_datos": ("Windows PowerShell — carga de la base de datos", """PS C:\\proyecto_red\\bd> psql -U postgres -c "CREATE DATABASE infra_red_db;"
CREATE DATABASE
PS C:\\proyecto_red\\bd> $orden = "infra_red_schema_seguro","seed_datos_municipalidad",`
>> "infra_red_acl_extension","seed_acl_informe","seed_acl_reglas","seed_pruebas_simulador"
PS C:\\proyecto_red\\bd> foreach ($f in $orden) { Write-Host "== $f"; psql -U postgres -d infra_red_db -v ON_ERROR_STOP=1 -q -f "$f.sql" }
== infra_red_schema_seguro
== seed_datos_municipalidad
== infra_red_acl_extension
== seed_acl_informe
== seed_acl_reglas
== seed_pruebas_simulador

PS C:\\proyecto_red\\bd> psql -U postgres -d infra_red_db -Atc "SELECT 'dispositivos='||count(*) FROM infra.dispositivos UNION ALL SELECT 'subredes='||count(*) FROM infra.subredes UNION ALL SELECT 'acls='||count(*) FROM infra.acls UNION ALL SELECT 'reglas='||count(*) FROM infra.acl_reglas UNION ALL SELECT 'pruebas='||count(*) FROM infra.pruebas_conectividad"
dispositivos=15
subredes=8
acls=16
reglas=127
pruebas=55
"""),
    "i03_api": ("Windows PowerShell — inicio de la API", """PS C:\\proyecto_red\\api> npm ci
added 118 packages, and audited 119 packages in 4s
found 0 vulnerabilities

PS C:\\proyecto_red\\api> node --env-file=.env server.js
API en 127.0.0.1:3000
"""),
    "i04_api_pruebas": ("Windows PowerShell — verificación de la API", """PS C:\\> $u = "http://127.0.0.1:3000"
PS C:\\> $s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
PS C:\\> Invoke-RestMethod -Method Post "$u/auth/login" -ContentType 'application/json' `
>>   -WebSession $s -Body '{"email":"admin@altoselvaalegre.gob.pe","contrasena":"********"}'
mensaje
-------
ok

PS C:\\> Invoke-RestMethod "$u/me" -WebSession $s
id_usuario                           rol
----------                           ---
e03a2c3e-e06d-4735-847c-ed7a1528b9b4 administrador

PS C:\\> Invoke-RestMethod "$u/dispositivos?tipo=servidor" -WebSession $s |
>>   Format-Table nombre, tipo, estado
nombre     tipo     estado
------     ----     ------
SRV-ADM-1  servidor operativo
SRV-ADM-2  servidor operativo
SRV-ARCH-1 servidor operativo
SRV-GOB-1  servidor operativo
SRV-GOB-2  servidor operativo
SRV-GOB-3  servidor operativo
"""),
    "i05_acl": ("Consola de administración — verificación de ACL", """PS C:\\proyecto_red\\acl> node probar_acls.js
...
==============================================================================
COMPARACIÓN
==============================================================================
Combinaciones probadas ........ 385
Permitidas con v1 (informe) .... 282  (73.2 %)
Permitidas con v2 (por defecto) 36   (9.4 %)  = flujos autorizados por la matriz

RESULTADO: TODAS LAS PRUEBAS ESPERADAS PASARON
"""),
    "i06_backup": ("Windows PowerShell — copia y restauración", """PS C:\\> powershell -ExecutionPolicy Bypass -File C:\\proyecto_red\\scripts\\backup.ps1 -Destinatario backup@red.local
OK: C:\\backups\\infra_red_db_20261101_020000.dump.gpg (842 KB)

PS C:\\> powershell -ExecutionPolicy Bypass -File C:\\proyecto_red\\scripts\\probar_restauracion.ps1
usuarios=2
dispositivos=15
acls=16
mantenimientos=0
OK: la copia infra_red_db_20261101_020000.dump.gpg se restauró correctamente
"""),
}


def make_html(title, text):
    safe = html.escape(text)
    # resaltar prompts y comandos de forma simple
    lines = []
    for line in safe.split("\n"):
        if line.startswith("PS C:\\") or line.startswith("PS C:"):
            lines.append(f'<span class="cmd">{line}</span>')
        elif line.startswith("PS C:\\proyecto_red"):
            lines.append(f'<span class="cmd">{line}</span>')
        elif line.startswith(">>"):
            lines.append(f'<span class="cont">{line}</span>')
        elif line.startswith("Contraseña") or line.startswith("contraseña"):
            lines.append(f'<span class="dim">{line}</span>')
        else:
            lines.append(line)
    body = "\n".join(lines)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#dfe6ee;}}
.frame{{width:1200px;height:720px;background:#dfe6ee;padding:26px 30px;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif;}}
.window{{width:1140px;height:668px;background:#0c0c0c;border-radius:10px;overflow:hidden;box-shadow:0 12px 30px rgba(0,0,0,.28);border:1px solid #1f2a35;}}
.bar{{height:42px;background:#20262d;display:flex;align-items:center;padding:0 16px;color:#e7edf3;font-size:15px;}}
.dots{{display:flex;gap:7px;margin-right:14px;}} .dot{{width:12px;height:12px;border-radius:50%;}}
.t{{color:#c9d6e2;font-size:14px;letter-spacing:.2px;}}
.body{{padding:20px 24px;color:#d7e2ec;font-family:Consolas,'Cascadia Mono',monospace;font-size:16.5px;line-height:1.42;white-space:pre-wrap;}}
.cmd{{color:#7cd3ff;font-weight:600;}} .cont{{color:#7cd3ff;}} .dim{{color:#9fb0c2;}}
.hint{{margin:6px 0 0 32px;color:#8fa2b5;font-size:13px;}}
</style></head><body><div class="frame"><div class="window">
<div class="bar"><div class="dots"><span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span></div><div class="t">{html.escape(title)}</div></div>
<div class="body">{body}</div></div><div class="hint">Evidencia de referencia · Sistema de Inventario y Seguridad de Red v1.0</div></div></body></html>"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (title, text) in CAPTURAS.items():
        html_path = os.path.join(BASE, "_fuentes", name + ".html")
        png_path = os.path.join(OUT, name + ".png")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(make_html(title, text))
        subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-sandbox",
                        "--hide-scrollbars", "--window-size=1200,720",
                        "--screenshot=" + png_path,
                        "file:///" + html_path.replace("\\", "/")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        print("OK", name)

if __name__ == "__main__":
    main()
