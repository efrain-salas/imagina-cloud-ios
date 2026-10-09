# Imagina Cloud para iPhone

Versión de la [app de Nextcloud para iOS](https://github.com/nextcloud/ios) con la marca de Imagina, fija a la nube de Imagina y con un único acceso: **«Entrar con Imagina»** (móvil y código SMS en una hoja del navegador que se cierra sola). Al entrar, la API de dispositivos de Imagina da de alta este iPhone y le entrega su acceso a Nextcloud (una contraseña de aplicación que solo él tiene); si Imagina lo desconecta, la app vuelve a «Entrar con Imagina». Desde su «Menú», **«Configurar el correo»** pone los buzones de Imagina en la app Mail del iPhone con un perfil de configuración (un enlace de un solo uso que da la misma API). Las notificaciones llegan por el servidor de notificaciones de Imagina. Forma parte del Cloud de Imagina: `docs/PLAN_CLOUD.md` en el repositorio de Imagina (hitos C11.2 y C11.5; prototipo en C0.12). La versión de Android es `imagina-cloud-android`, con el mismo principio.

- **Versión de Nextcloud**: `35.1.0` (`NEXTCLOUD_IOS_TAG`), el remoto `upstream`.
- **Licencia**: GPL v3 (la de la app de Nextcloud para iOS). El código de esta versión tiene que estar publicado (`IMAGINA_SOURCE_CODE_URL`, que la app enseña en Ajustes).
- **Marca**: la app no puede llevar «Nextcloud» en el nombre ni su logo, y dice que no es la oficial y que está modificada en el pie de Ajustes («Imagina Cloud for iOS x.y.z, a modified version of Nextcloud for iOS (not the official app)») y, cuando exista, en su ficha ([directrices de marca de Nextcloud](https://nextcloud.com/trademarks/)). Por eso se sustituyen el icono y el logo.

## Principio: todo cambio, aparte, parametrizado y regenerable

La app de Nextcloud para iOS se personaliza editando sus ficheros de marca (`Brand/`) y el proyecto de Xcode. Aquí esas ediciones no se hacen a mano: **las hace `imagina/apply-branding.py`**, que parte siempre del fichero tal como lo publica Nextcloud en `NEXTCLOUD_IOS_TAG` (`git show <tag>:<fichero>`), aplica los cambios y lo escribe. Cada cambio busca un trozo exacto del código de Nextcloud y se para con un error si no lo encuentra.

- Lo de Imagina vive en ficheros que Nextcloud no tiene (`imagina/`, `IMAGINA.md`).
- Los ficheros de Nextcloud que cambian son solo los que escribe el script (tabla de abajo), y su resultado se guarda en git para que el proyecto se abra y compile en Xcode tal cual.
- Lo que cambia entre entornos va en `imagina/imagina.properties`; nada de Imagina está escrito a mano en un fichero de Nextcloud.

## Compilar

Requisitos: Xcode 27 con la cuenta de desarrollador de Imagina (equipo `CF798UCN8C`) en Ajustes › Cuentas.

```sh
python3 -I imagina/apply-branding.py
xcodebuild -project Nextcloud.xcodeproj -scheme Nextcloud -configuration Debug \
  -destination 'id=<UDID del iPhone>' -allowProvisioningUpdates build
```

La firma es automática: la primera vez Xcode crea el certificado de desarrollo, los identificadores de la app y sus extensiones y los grupos de app. Para instalarla en un iPhone conectado:

```sh
xcrun devicectl device install app --device <UDID> \
  ~/Library/Developer/Xcode/DerivedData/Nextcloud-*/Build/Products/Debug-iphoneos/Nextcloud.app
```

`apply-branding.py` hay que ejecutarlo después de clonar (genera `imagina/Sources/ImaginaParameters.swift`, que no está en git) y siempre que cambien los parámetros, las imágenes o la versión de Nextcloud.

## Parámetros

`imagina/imagina.properties` (en git, sin secretos):

| Clave | Para qué |
| --- | --- |
| `NEXTCLOUD_IOS_TAG` | Versión de Nextcloud de la que parte la marca. |
| `IMAGINA_APPLICATION_ID` | Id de la app (`build.imagina.cloud`); las extensiones son `<id>.<extensión>` y los grupos de app `group.<id>` y `group.<id>.apps`. El OAuth vuelve a `<id>://oauth2redirect`. |
| `IMAGINA_DEVELOPMENT_TEAM` | Equipo de Apple que firma la app. |
| `IMAGINA_APP_NAME` | Nombre bajo el icono, en la app Archivos y en la hoja de compartir. |
| `IMAGINA_URL_SCHEME` | Esquema de los enlaces propios de la app (widgets, enlaces profundos) en lugar de `nextcloud`, para no abrir la app oficial. |
| `IMAGINA_CLOUD_URL` | La nube a la que la app está fija (producción, `https://cloud.imagina.build`). El acceso de cada dispositivo (dirección, usuario y contraseña de aplicación) lo da la API de dispositivos; este valor es solo el de la marca de Nextcloud. |
| `IMAGINA_PUSH_SERVER_URL` | Servidor de notificaciones de Imagina (`https://auth.imagina.build/api/push`; habla el protocolo del proxy de notificaciones de Nextcloud y manda con APNs de producción para el topic `IMAGINA_APPLICATION_ID`). Vacío: sin notificaciones. |
| `IMAGINA_AUTH_HOST` | Servidor de identidad de Imagina, que también sirve la API de dispositivos (`/api/v1/cloud/devices`). Vacío: la app usa el acceso de Nextcloud. |
| `IMAGINA_OAUTH_CLIENT_ID` | Cliente OAuth público de Imagina Cloud en Imagina (el mismo que Android). |
| `IMAGINA_PRIVACY_URL`, `IMAGINA_APP_STORE_URL`, `IMAGINA_SOURCE_CODE_URL` | Enlaces de Ajustes. |
| `IMAGINA_ACCENT` | Color del tema (el acento de Imagina); el tema del servidor puede sustituirlo. |

`imagina/imagina.local.properties` (fuera de git) sobrescribe o añade claves en cada máquina (por ejemplo, otro `IMAGINA_AUTH_HOST` para probar contra un servidor de pruebas). Los parámetros de prueba del prototipo (`IMAGINA_TEST_NC_USER`, `IMAGINA_TEST_NC_APP_PASSWORD`, `IMAGINA_TEST_MAIL_PROFILE_URL`) ya no los lee ni el código ni el script: se pueden borrar de ese fichero.

## Cambios en ficheros de Nextcloud (los escribe el script)

| Fichero | Cambio | Motivo |
| --- | --- | --- |
| `Nextcloud.xcodeproj/project.pbxproj` | Ids de la app y de sus extensiones, equipo de firma (también a nivel de proyecto), la carpeta `imagina/Sources` sincronizada en el target `Nextcloud` y la fase «Crashlytics dSYM Upload» vacía. | Convivir con la app oficial, firmar con la cuenta de Imagina, compilar el código de Imagina sin listar ficheros a mano y no mandar nada a Firebase. |
| `Nextcloud.xcodeproj/xcshareddata/xcschemes/*.xcscheme` | Ids de las extensiones. | Que los esquemas de depuración encuentren la app. |
| `Brand/*.entitlements` | Grupos de app y grupo del llavero propios. | Los de Nextcloud son de su equipo. La app lleva `aps-environment` (Xcode lo cambia a `production` al firmar para TestFlight o el App Store); la extensión de notificaciones comparte grupo de app y llavero con la app y no necesita más. |
| `Brand/iOSClient.plist` | Nombre, id del esquema de URL y esquema `IMAGINA_URL_SCHEME`. | Marca y enlaces propios. |
| `Brand/File_Provider_Extension.plist`, `File_Provider_Extension_UI.plist`, `Share.plist`, `Action_Assistant.plist` | Nombre y grupo de app. | El nombre que se ve en Archivos y al compartir. |
| `Brand/BackgroundUploadExtension.plist` | La nube de `IMAGINA_CLOUD_URL` en lugar de `cloud.nextcloud.com` como URL base (ningún código la lee). | Que no quede ninguna dirección de Nextcloud. |
| `Brand/NCBrand.swift` | Opciones de marca: nombre, agente de usuario, aviso de «versión modificada, no es la oficial» (pie de Ajustes), nube fija, servidor de notificaciones (`pushNotificationServerProxy`; sin él Nextcloud usaría el suyo solo si la marca fuera «Nextcloud», que no lo es), enlaces, enlace al código fuente visible en Ajustes, grupos, sin introducción, una sola cuenta, sin informes de fallos ni perfiles de Nextcloud, color. | Lo que Nextcloud deja cambiar a las versiones con otra marca. |
| `Brand/LaunchScreen.storyboard` | Fondo con el acento de Imagina. | Pantalla de carga. |
| `iOSClient/NCGlobal.swift` | Esquema de la app y de las acciones de los widgets. | Que los enlaces no abran la app oficial. |
| `iOSClient/More/NCMoreModel.swift` | Tres enganches marcados «Imagina (IMAGINA.md)»: un destino `imagina` para las acciones de Imagina, su caso en `perform` y la fila «Configurar el correo» (o «Actualizar el correo») encima de «Configuración». La fila solo aparece mientras este iPhone es un dispositivo conectado; el enganche pasa una función para volver a construir el Menú cuando cambia el estado del perfil. | Que el correo del iPhone se configure desde la app. |
| `iOSClient/Login/NCLogin.swift` | Un enganche al final de `viewDidLoad`, marcado «Imagina (IMAGINA.md)»: pone «Entrar con Imagina» en lugar de la dirección del servidor. Inactivo si `IMAGINA_AUTH_HOST` está vacío. | El acceso de Nextcloud enseña sus páginas y pide autorizar dos veces. También es la pantalla a la que Nextcloud lleva cuando la contraseña de aplicación deja de valer (ver abajo). |
| `iOSClient/Account/Account Settings/NCAccountSettingsModel.swift` | Una línea tras quitar la cuenta, marcada «Imagina (IMAGINA.md)»: desconecta este iPhone en Imagina. | Que quitar la cuenta libere el dispositivo (y su plaza) en Imagina. |
| `Notification Service Extension/NotificationService.swift` | El texto de reserva de una notificación que no se puede leer dice el nombre de la app en lugar de «Nextcloud». | Marca. |
| `iOSClient/Supporting Files/*.lproj/Localizable.strings` | El texto que nombra la app en Ajustes del iPhone (`_access_photo_not_enabled_msg_`) dice `IMAGINA_APP_NAME`. | Los demás textos con «Nextcloud» hablan del servidor o usan ya el nombre de marca. |
| `AppIcon.icon`, `Brand/Custom.xcassets/AppIcon.appiconset`, `Brand/Custom.xcassets/logo.imageset` | Icono y logo de Imagina Cloud (ver abajo). | Marca. |

## Lo propio de Imagina

| Dónde | Qué |
| --- | --- |
| `imagina/apply-branding.py` | Aplica todo lo anterior desde la versión de Nextcloud de `NEXTCLOUD_IOS_TAG`. |
| `imagina/Sources/ImaginaSignIn.swift` | «Entrar con Imagina»: el botón de la pantalla de acceso y OAuth con PKCE (alcance `openid cloud.devices`) contra Imagina en una `ASWebAuthenticationSession` efímera (sin el aviso «quiere usar … para iniciar sesión») que vuelve por `<id>://oauth2redirect`. Si Imagina rechaza (sin plaza, la Cloud de la persona aún no está lista…) enseña su mensaje con «Reintentar». |
| `imagina/Sources/ImaginaDevice.swift` | Este iPhone como dispositivo de Imagina: lo da de alta (`POST /devices`, plataforma `IOS`, nombre `UIDevice.current.name`) y devuelve el acceso a Nextcloud; al quitar la cuenta lo desconecta (`DELETE`). |
| `imagina/Sources/ImaginaApi.swift` | Las peticiones a Imagina: endpoint de tokens (con renovación; el refresh token rota) y API de dispositivos (`POST`, `GET /{id}`, `POST /{id}/mail-profile`, `DELETE /{id}`). Una renovación a la vez; los rechazos de Imagina (`{"error","message"}`) llegan a la persona con su texto. |
| `imagina/Sources/ImaginaStore.swift` | El llavero propio (no el de Nextcloud): id del dispositivo, tokens y último estado del perfil de correo, solo en este iPhone y sin copia de seguridad. Sobrevive a borrar la app. |
| `imagina/Sources/ImaginaMailSetup.swift` | «Configurar el correo»: explica los pasos que quedan en Ajustes (Permitir, Perfil descargado, Instalar), pide a la API un enlace de un solo uso (válido unos minutos) y lo abre en Safari, que es el único que puede instalar el perfil. Lo ofrece también justo después de «Entrar con Imagina». |
| `imagina/Sources/ImaginaBrand.swift` | Colores del manual de marca y textos de las pantallas de Imagina (español de España, tuteo; inglés en los demás idiomas). |
| `imagina/Sources/ImaginaParameters.swift` | Generado por el script con los parámetros; fuera de git. |
| `imagina/brand/` | Fuentes de las imágenes de marca. |
| `imagina/GoogleService-Info.placeholder.plist` | Sustituto del fichero de Firebase que Nextcloud deja fuera de git y su proyecto copia en la app; el script lo pone en la raíz si no hay otro. Nunca se usa: la app no manda informes de fallos. |

## Cómo se conecta el iPhone

1. **Entrar**: «Entrar con Imagina» (OAuth, tokens en el llavero) → `POST /api/v1/cloud/devices` crea el dispositivo y devuelve `cloud.url`, `cloud.loginName` y `cloud.appPassword` → la app crea con eso su única cuenta de Nextcloud. Si había un dispositivo guardado de antes (se borró la app, se reinició o se perdió la cuenta), se desconecta antes de crear el nuevo: Imagina no entrega dos veces la contraseña de aplicación de un dispositivo y así no se gasta otra plaza.
2. **Tokens**: el de acceso dura 15 minutos y el de renovación 7 días (rota en cada uso). Al pedir el perfil de correo, si no se pueden renovar, se vuelve a «Entrar con Imagina» solo para conseguir un token: no se crea otro dispositivo, se sigue con el id guardado.
3. **Correo**: el Menú muestra «Configurar el correo» mientras este iPhone sea un dispositivo conectado (o «Actualizar el correo» si Imagina dice que el perfil instalado ya no coincide con los buzones: `GET /devices/{id}` → `mailProfile`). Al tocarlo se enseña el paso a paso de Ajustes y, al descargar, `POST /devices/{id}/mail-profile` da un enlace nuevo que se abre en Safari. Si Imagina contesta que el dispositivo está desconectado (410), la app lo olvida y lo dice.
4. **Imagina desconecta el dispositivo**: la contraseña de aplicación deja de valer, Nextcloud recibe un 401 (`NCMainTabBarController` lo comprueba cada 3 segundos → `NCAccount.checkRemoteUser`), quita la cuenta y presenta `NCLogin`, que aquí es el botón «Entrar con Imagina». Al volver a entrar se crea la cuenta de cero (la app es de una sola cuenta); el dispositivo guardado, si Imagina ya lo da por desconectado, se descarta y se crea otro.
5. **La persona quita la cuenta** en la app: se desconecta el dispositivo en Imagina (`DELETE`, sin esperar) y se borran del llavero el id y los tokens.

### Notificaciones (C11.5)

La app se registra, como la de Nextcloud, en el servidor de Nextcloud de la persona (`notifications`) indicando `IMAGINA_PUSH_SERVER_URL` como proxy, y en ese proxy (`POST …/devices`) con su token de APNs. Hacen falta `aps-environment` en la app (ya está) y los modos de fondo `remote-notification` (ya están). Nada apunta ya al proxy de Nextcloud (`push-notifications.nextcloud.com`) ni a Firebase: `FirebaseApp.configure()` no se llama (`disable_crash_service`) y la fase de Crashlytics está vacía. El servidor de Imagina manda con APNs de producción, así que las notificaciones solo llegan a compilaciones de TestFlight o del App Store, no a las de Xcode en un iPhone (esas usan el APNs de desarrollo).

## Imágenes de marca

En `imagina/brand/`: `imagina-cloud-mark.svg` (la loseta tinta de Imagina con la nube y el punto teal, la misma que en Android), `imagina-cloud-icon-square.svg` (la misma a sangre, para el PNG del icono), `AppIcon-1024.png` y `AppIcon.icon` (el icono de Icon Composer: fondo tinta, la nube en marfil y el punto teal, sin brillo ni translucidez). El script las copia en su sitio. Para regenerar el PNG tras cambiar el SVG:

```sh
qlmanage -t -s 1024 -o /tmp imagina/brand/imagina-cloud-icon-square.svg
sips -s format png -z 1024 1024 /tmp/imagina-cloud-icon-square.svg.png --out imagina/brand/AppIcon-1024.png
```

## Actualizar a una nueva versión de Nextcloud

1. `git fetch upstream --tags` y `git merge <nueva>` sobre `main`. Los conflictos en ficheros que escribe el script se resuelven quedándose con cualquiera de las dos versiones: el paso 3 los reescribe.
2. Cambiar `NEXTCLOUD_IOS_TAG` en `imagina/imagina.properties`.
3. `python3 -I imagina/apply-branding.py`. Si se para, Nextcloud cambió el trozo que el script busca: revisar el cambio en Nextcloud y ajustar el script.
4. Revisar opciones de marca nuevas: `git diff <anterior> <nueva> -- Brand/NCBrand.swift`, y extensiones o grupos de app nuevos: `git diff <anterior> <nueva> -- Brand/ Nextcloud.xcodeproj/project.pbxproj | grep -i 'twsweb\|group\.'`.
5. Compilar e instalar en un iPhone y probar: «Entrar con Imagina» (la hoja se cierra sola y, al crearse la cuenta, ofrece configurar el correo), lista de ficheros, subir una foto, la app en Archivos, «Menú › Configurar el correo» hasta «Perfil instalado», desconectar el dispositivo desde Imagina y ver que la app vuelve a «Entrar con Imagina», y que no se vea «Nextcloud» en ninguna pantalla.

## Pendiente para la app de verdad

- Probar de punta a punta con un móvil real (necesita el SMS): alta del dispositivo, cuenta, perfil de correo y reentrada tras desconectar. Está compilado y revisado, pero no ejecutado.
- Notificaciones: probar en TestFlight con la clave de APNs de Imagina. La app se registra con el agente de usuario de Nextcloud más `-Imagina` y el sufijo `(Strict VoIP)` que añade Nextcloud iOS; el servidor de Imagina tiene que tratarlo como el proxy de Nextcloud.
- Restablecer la app (tras fallar el código demasiadas veces) borra las cuentas sin avisar a Imagina; el siguiente «Entrar con Imagina» desconecta el dispositivo anterior y crea otro, pero hasta entonces ocupa plaza.
- El perfil de correo tiene que ir firmado (si no, iOS añade «Perfil sin firmar»): lo firma el servidor de Imagina (C7.2).
- Firma de distribución, ficha del App Store, `ITSEncryptionExportComplianceCode` propio (el de `iOSClient.plist` es de Nextcloud) y aviso de «no es la app oficial» en la ficha.
