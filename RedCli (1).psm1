#Requires -Version 5.1
<#
  RedCli.psm1 - Consola de gestión de la red (inventario, mantenimientos, usuarios).
  Habla con la API del proyecto; cada comando respeta el rol del usuario (consulta, tecnico, administrador).
  Carga:   Import-Module C:\proyecto_red\scripts\RedCli.psm1 -Force
  Ayuda:   Get-Command -Module RedCli      |      Get-Help Connect-Red -Examples
  Probado con PowerShell 7 (Linux). Compatible con Windows PowerShell 5.1 pero NO probado en Windows.
#>

$script:Red = @{ Url = $null; Sesion = $null }

function ConvertTo-TextoPlano([SecureString]$Segura) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Segura)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function ConvertTo-RedError($e, [string]$Contexto) {
    $codigo = 0
    try { $codigo = [int]$e.Exception.Response.StatusCode } catch { }
    $detalle = ''
    if ($e.ErrorDetails -and $e.ErrorDetails.Message) {
        try { $detalle = ($e.ErrorDetails.Message | ConvertFrom-Json).error } catch { }
    }
    if (-not $detalle -and $e.Exception.Response -and $e.Exception.Response.GetResponseStream) {
        try { $detalle = (([IO.StreamReader]::new($e.Exception.Response.GetResponseStream())).ReadToEnd() | ConvertFrom-Json).error } catch { }
    }
    $msg = switch ($codigo) {
        400 { "Datos no válidos. Revise los valores indicados. $detalle" }
        401 { if ($Contexto -eq 'login') { 'Correo o contraseña incorrectos. Cinco fallos seguidos bloquean la cuenta 15 minutos.' }
              else { 'La sesión no es válida o caducó (30 minutos sin actividad). Vuelva a ejecutar Connect-Red.' } }
        403 { 'Su rol no permite esta acción. Si cree que debería, consulte a un administrador.' }
        404 { 'No se encontró el registro, o su rol no puede verlo.' }
        409 { 'Ya existe un registro igual (nombre o correo repetido).' }
        429 { 'Demasiados intentos en poco tiempo. Espere unos minutos e intente de nuevo.' }
        0   { "No se pudo contactar con el servidor ($($script:Red.Url)). Verifique que la API esté activa. $($e.Exception.Message)" }
        default { "Error $codigo del servidor. $detalle" }
    }
    [System.Exception]::new($msg)
}

function Get-RedCsrf {
    foreach ($c in $script:Red.Sesion.Cookies.GetCookies([Uri]$script:Red.Url)) {
        if ($c.Name -in 'csrf', '__Host-csrf') { return $c.Value }
    }
    throw 'No se encontró el token de seguridad (CSRF). Vuelva a ejecutar Connect-Red.'
}

function Invoke-RedApi {
    param([string]$Metodo = 'GET', [Parameter(Mandatory)][string]$Ruta, $Cuerpo, [string]$Contexto = '')
    if (-not $script:Red.Sesion) { throw 'No hay sesión activa. Ejecute primero: Connect-Red -Url http://servidor:3000 -Correo usted@dominio.pe' }
    $p = @{ Method = $Metodo; Uri = ($script:Red.Url + $Ruta); WebSession = $script:Red.Sesion; ErrorAction = 'Stop' }
    if ($Metodo -ne 'GET') { $p.Headers = @{ 'X-CSRF-Token' = (Get-RedCsrf) } }
    if ($null -ne $Cuerpo) {
        $p.ContentType = 'application/json; charset=utf-8'
        $p.Body = [Text.Encoding]::UTF8.GetBytes(($Cuerpo | ConvertTo-Json -Depth 5 -Compress))
    }
    try { Invoke-RestMethod @p } catch { throw (ConvertTo-RedError $_ $Contexto) }
}

function Resolve-RedDispositivo([string]$Dispositivo) {
    if ($Dispositivo -match '^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$') { return $Dispositivo }
    $lista = @(Invoke-RedApi -Ruta '/dispositivos' | Where-Object { $_.nombre -eq $Dispositivo })
    if ($lista.Count -ne 1) { throw "No se encontró un dispositivo llamado '$Dispositivo'. Use Get-RedDispositivo para ver los nombres exactos." }
    $lista[0].id_dispositivo
}

function Connect-Red {
    <#
    .SYNOPSIS Inicia sesión en la API de la red.
    .EXAMPLE Connect-Red -Url http://127.0.0.1:3000 -Correo tecnico@dominio.pe
    #>
    param([Parameter(Mandatory)][string]$Url, [Parameter(Mandatory)][string]$Correo, [SecureString]$Contrasena)
    if (-not $Contrasena) { $Contrasena = Read-Host 'Contraseña' -AsSecureString }
    $sesion = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $cuerpo = @{ email = $Correo; contrasena = (ConvertTo-TextoPlano $Contrasena) } | ConvertTo-Json -Compress
    try {
        Invoke-RestMethod -Method Post -Uri ($Url.TrimEnd('/') + '/auth/login') -ContentType 'application/json; charset=utf-8' `
            -Body ([Text.Encoding]::UTF8.GetBytes($cuerpo)) -WebSession $sesion -ErrorAction Stop | Out-Null
    } catch { $script:Red.Url = $Url.TrimEnd('/'); throw (ConvertTo-RedError $_ 'login') }
    $script:Red.Url = $Url.TrimEnd('/'); $script:Red.Sesion = $sesion
    Get-RedYo
}

function Disconnect-Red {
    <# .SYNOPSIS Cierra la sesión (la invalida también en el servidor). #>
    if ($script:Red.Sesion) { try { Invoke-RedApi -Metodo POST -Ruta '/auth/logout' | Out-Null } catch { } }
    $script:Red.Sesion = $null
    Write-Host 'Sesión cerrada.'
}

function Get-RedYo {
    <# .SYNOPSIS Muestra quién es usted y qué rol tiene. #>
    $r = Invoke-RedApi -Ruta '/me'
    [pscustomobject]@{ Id = $r.id_usuario; Rol = $r.rol; Servidor = $script:Red.Url }
}

function Set-RedContrasena {
    <#
    .SYNOPSIS Cambia su contraseña (cierra todas sus sesiones; debe conectarse de nuevo).
    Requisitos: 12+ caracteres, mayúscula, minúscula, número y símbolo; máximo 72 bytes.
    #>
    param([SecureString]$Actual, [SecureString]$Nueva)
    if (-not $Actual) { $Actual = Read-Host 'Contraseña actual' -AsSecureString }
    if (-not $Nueva)  { $Nueva  = Read-Host 'Contraseña nueva'  -AsSecureString }
    Invoke-RedApi -Metodo POST -Ruta '/auth/cambiar-contrasena' -Cuerpo @{ actual = (ConvertTo-TextoPlano $Actual); nueva = (ConvertTo-TextoPlano $Nueva) } | Out-Null
    $script:Red.Sesion = $null
    Write-Host 'Contraseña cambiada. Se cerraron sus sesiones: ejecute Connect-Red otra vez.'
}

function Get-RedDispositivo {
    <#
    .SYNOPSIS Lista dispositivos o muestra el detalle de uno.
    .EXAMPLE Get-RedDispositivo -Tipo servidor
    .EXAMPLE Get-RedDispositivo -Nombre firewall
    .EXAMPLE Get-RedDispositivo -Id 3ae8e31c-3810-4fa1-9ebd-229762d60f5e
    #>
    param(
        [ValidateSet('firewall','router','switch','access_point','servidor','ups','onu','radioenlace','modem','otro')][string]$Tipo,
        [ValidateSet('operativo','en_mantenimiento','averiado','retirado','propuesto')][string]$Estado,
        [string]$Nombre, [string]$Id)
    if ($Id) { return Invoke-RedApi -Ruta "/dispositivos/$Id" }
    $q = @(); if ($Tipo) { $q += "tipo=$Tipo" }; if ($Estado) { $q += "estado=$Estado" }
    $ruta = '/dispositivos' + $(if ($q) { '?' + ($q -join '&') } else { '' })
    Invoke-RedApi -Ruta $ruta | Where-Object { -not $Nombre -or $_.nombre -like "*$Nombre*" } | ForEach-Object {
        [pscustomobject]@{ Nombre = $_.nombre; Tipo = $_.tipo; Marca = $_.marca; Modelo = $_.modelo; Estado = $_.estado
                           Sede = $_.sede; Piso = $_.piso; Ambiente = $_.ambiente; Id = $_.id_dispositivo }
    }
}

function Get-RedVlan {
    <# .SYNOPSIS Lista las VLAN (actuales y propuestas). #>
    Invoke-RedApi -Ruta '/vlans' | ForEach-Object {
        [pscustomobject]@{ Numero = $_.numero; Nombre = $_.nombre; Funcion = $_.funcion; Diseno = $_.estado_diseno } }
}

function Get-RedSubred {
    <# .SYNOPSIS Lista las subredes con su capacidad y las IP registradas. #>
    Invoke-RedApi -Ruta '/subredes' | ForEach-Object {
        [pscustomobject]@{ Red = $_.red; Diseno = $_.estado_diseno; Funcion = $_.funcion
                           Capacidad = [int]$_.capacidad_hosts; IPRegistradas = [int]$_.ips_registradas } }
}

function Get-RedMantenimiento {
    <#
    .SYNOPSIS Lista los mantenimientos, o los próximos a vencer con -Proximos.
    .EXAMPLE Get-RedMantenimiento
    .EXAMPLE Get-RedMantenimiento -Proximos
    #>
    param([switch]$Proximos)
    if ($Proximos) {
        Invoke-RedApi -Ruta '/mantenimientos/proximos' | ForEach-Object {
            [pscustomobject]@{ Dispositivo = $_.nombre; Tipo = $_.tipo; UltimoMantenimiento = $_.ultimo_mantenimiento; Proximo = $_.proximo } }
    } else {
        Invoke-RedApi -Ruta '/mantenimientos' | ForEach-Object {
            [pscustomobject]@{ Dispositivo = $_.dispositivo; Tipo = $_.tipo; Descripcion = $_.descripcion; Estado = $_.estado
                               Programada = $_.fecha_programada; Realizada = $_.fecha_realizada; Id = $_.id_mantenimiento } }
    }
}

function New-RedMantenimiento {
    <#
    .SYNOPSIS Programa un mantenimiento (usted queda como responsable). Roles: tecnico, administrador.
    .EXAMPLE New-RedMantenimiento -Dispositivo FW-FORTIGATE-90G -Descripcion 'Revision anual' -Fecha 2026-12-01
    #>
    param([Parameter(Mandatory)][string]$Dispositivo, [Parameter(Mandatory)][string]$Descripcion,
          [Parameter(Mandatory)][string]$Fecha, [ValidateSet('preventivo','correctivo','inspeccion')][string]$Tipo = 'preventivo')
    if ($Fecha -notmatch '^\d{4}-\d{2}-\d{2}$') { throw "La fecha debe tener el formato AAAA-MM-DD (por ejemplo 2026-12-01)." }
    $id = Resolve-RedDispositivo $Dispositivo
    $r = Invoke-RedApi -Metodo POST -Ruta '/mantenimientos' -Cuerpo @{ id_dispositivo = $id; tipo = $Tipo; descripcion = $Descripcion; fecha_programada = $Fecha }
    [pscustomobject]@{ Id = $r.id_mantenimiento; Dispositivo = $Dispositivo; Programada = $Fecha; Estado = 'programado' }
}

function Set-RedMantenimiento {
    <#
    .SYNOPSIS Cambia el estado de un mantenimiento propio (el administrador puede cambiar cualquiera).
    .EXAMPLE Set-RedMantenimiento -Id <uuid> -Estado completado -FechaRealizada 2026-12-02
    #>
    param([Parameter(Mandatory)][string]$Id, [ValidateSet('programado','en_curso','completado','cancelado')][string]$Estado, [string]$FechaRealizada)
    $c = @{}; if ($Estado) { $c.estado = $Estado }; if ($FechaRealizada) { $c.fecha_realizada = $FechaRealizada }
    if (-not $c.Count) { throw 'Indique -Estado y/o -FechaRealizada.' }
    if ($Estado -eq 'completado' -and -not $FechaRealizada) { throw "Para marcar 'completado' indique también -FechaRealizada AAAA-MM-DD." }
    $r = Invoke-RedApi -Metodo PATCH -Ruta "/mantenimientos/$Id" -Cuerpo $c
    [pscustomobject]@{ Id = $r.id_mantenimiento; Estado = $r.estado; Realizada = $r.fecha_realizada }
}

function New-RedDispositivo {
    <#
    .SYNOPSIS Registra un dispositivo. Rol: administrador.
    .EXAMPLE New-RedDispositivo -Nombre SW-PISO3-01 -Tipo switch -Marca TP-Link -MantenimientoCadaMeses 12
    #>
    param([Parameter(Mandatory)][string]$Nombre,
          [Parameter(Mandatory)][ValidateSet('firewall','router','switch','access_point','servidor','ups','onu','radioenlace','modem','otro')][string]$Tipo,
          [string]$Marca, [string]$Modelo, [string]$IdUbicacion, [ValidateRange(1,120)][int]$MantenimientoCadaMeses, [string]$Observaciones)
    $c = @{ nombre = $Nombre; tipo = $Tipo }
    if ($Marca) { $c.marca = $Marca }; if ($Modelo) { $c.modelo = $Modelo }; if ($IdUbicacion) { $c.id_ubicacion = $IdUbicacion }
    if ($MantenimientoCadaMeses) { $c.mantenimiento_cada_meses = $MantenimientoCadaMeses }; if ($Observaciones) { $c.observaciones = $Observaciones }
    $r = Invoke-RedApi -Metodo POST -Ruta '/dispositivos' -Cuerpo $c
    [pscustomobject]@{ Id = $r.id_dispositivo; Nombre = $Nombre; Tipo = $Tipo }
}

function Get-RedUsuario {
    <# .SYNOPSIS Lista los usuarios (nunca muestra contraseñas). Rol: administrador. #>
    Invoke-RedApi -Ruta '/admin/usuarios' | ForEach-Object {
        [pscustomobject]@{ Nombre = $_.nombre; Correo = $_.email; Rol = $_.rol; Activo = $_.activo; Registro = $_.fecha_registro; Id = $_.id_usuario } }
}

function New-RedUsuario {
    <#
    .SYNOPSIS Crea un usuario. Rol: administrador. La contraseña inicial debe cumplir la política (12+ caracteres, etc.).
    .EXAMPLE New-RedUsuario -Nombre 'Ana Perez' -Correo ana@dominio.pe -Rol tecnico
    #>
    param([Parameter(Mandatory)][string]$Nombre, [Parameter(Mandatory)][string]$Correo,
          [ValidateSet('administrador','tecnico','consulta')][string]$Rol = 'consulta', [SecureString]$Contrasena)
    if (-not $Contrasena) { $Contrasena = Read-Host 'Contraseña inicial' -AsSecureString }
    $r = Invoke-RedApi -Metodo POST -Ruta '/admin/usuarios' -Cuerpo @{ nombre = $Nombre; email = $Correo; contrasena = (ConvertTo-TextoPlano $Contrasena); rol = $Rol }
    [pscustomobject]@{ Id = $r.id_usuario; Nombre = $Nombre; Correo = $Correo; Rol = $Rol }
}

Export-ModuleMember -Function Connect-Red, Disconnect-Red, Get-RedYo, Set-RedContrasena, Get-RedDispositivo, Get-RedVlan,
    Get-RedSubred, Get-RedMantenimiento, New-RedMantenimiento, Set-RedMantenimiento, New-RedDispositivo, Get-RedUsuario, New-RedUsuario
