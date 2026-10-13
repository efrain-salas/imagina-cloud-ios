# Imagina Cloud para iPhone

Versión de la [app de Nextcloud para iOS](https://github.com/nextcloud/ios) con la marca de Imagina, fija a la nube de Imagina y con un único acceso: **«Entrar con Imagina»** (móvil y código SMS en una hoja del navegador que se cierra sola). Al entrar, la API de dispositivos de Imagina da de alta este iPhone y le entrega su acceso a Nextcloud (una contraseña de aplicación que solo él tiene); si Imagina lo desconecta, la app vuelve a «Entrar con Imagina». Desde su «Menú», **«Configurar el correo»** pone los buzones de Imagina en la app Mail del iPhone con un perfil de configuración (un enlace de un solo uso que da la misma API). Las notificaciones llegan por el servidor de notificaciones de Imagina, y el correo nuevo de los buzones que lee la app Mail de este iPhone también avisa (tocar el aviso abre el mensaje en Mail). Forma parte del Cloud de Imagina: `docs/PLAN_CLOUD.md` en el repositorio de Imagina (hitos C11.2, C11.5 y C12.6; prototipo en C0.12). La versión de Android es `imagina-cloud-android`, con el mismo principio.

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
| `IMAGINA_ACCENT` | Color del tema (el acento de Imagina, teal): solo para resaltar (botones, selección, interruptores, carpetas). El tema del servidor puede sustituirlo: la app solo lee de él `color-element` y `color-text`, no `color` ni `background`. |
| `IMAGINA_CANVAS`, `IMAGINA_CANVAS_DARK` | El lienzo de Imagina (crema `#F8F7F4`; `#111219` en el tema oscuro): fondo de las pantallas que pinta la marca (carga, acceso, error de la app Archivos, mantenimiento) y de las principales (Archivos, Favoritos, Media, Menú). |
| `IMAGINA_INK`, `IMAGINA_INK_DARK` | La tinta (`#1A1B25`; `#F3F2EE` en oscuro): el texto sobre el lienzo. |

`imagina/imagina.local.properties` (fuera de git) sobrescribe o añade claves en cada máquina (por ejemplo, otro `IMAGINA_AUTH_HOST` para probar contra un servidor de pruebas). Los parámetros de prueba del prototipo (`IMAGINA_TEST_NC_USER`, `IMAGINA_TEST_NC_APP_PASSWORD`, `IMAGINA_TEST_MAIL_PROFILE_URL`) ya no los lee ni el código ni el script: se pueden borrar de ese fichero.

## Cambios en ficheros de Nextcloud (los escribe el script)

| Fichero | Cambio | Motivo |
| --- | --- | --- |
| `Nextcloud.xcodeproj/project.pbxproj` | Ids de la app y de sus extensiones, equipo de firma (también a nivel de proyecto), la carpeta `imagina/Sources` sincronizada en el target `Nextcloud` y la fase «Crashlytics dSYM Upload» vacía. | Convivir con la app oficial, firmar con la cuenta de Imagina, compilar el código de Imagina sin listar ficheros a mano y no mandar nada a Firebase. |
| `Nextcloud.xcodeproj/xcshareddata/xcschemes/*.xcscheme` | Ids de las extensiones. | Que los esquemas de depuración encuentren la app. |
| `Brand/*.entitlements` | Grupos de app y grupo del llavero propios. | Los de Nextcloud son de su equipo. La app lleva `aps-environment` (Xcode lo cambia a `production` al firmar para TestFlight o el App Store); la extensión de notificaciones comparte grupo de app y llavero con la app y no necesita más. |
| `Brand/iOSClient.plist` | Nombre, id del esquema de URL y esquema `IMAGINA_URL_SCHEME`; `UIAppFonts` con las cuatro Instrument Sans de `imagina/Sources/Fonts` (van en la raíz del paquete) y barra de estado `UIStatusBarStyleDefault` (la pantalla de carga ya no es teal con texto claro, sino lienzo claro u oscuro). | Marca, enlaces propios y tipografía. |
| `Brand/File_Provider_Extension.plist`, `File_Provider_Extension_UI.plist`, `Share.plist`, `Action_Assistant.plist` | Nombre y grupo de app. | El nombre que se ve en Archivos y al compartir. |
| `Brand/BackgroundUploadExtension.plist` | La nube de `IMAGINA_CLOUD_URL` en lugar de `cloud.nextcloud.com` como URL base (ningún código la lee). | Que no quede ninguna dirección de Nextcloud. |
| `Brand/NCBrand.swift` | Opciones de marca: nombre, agente de usuario, aviso de «versión modificada, no es la oficial» (pie de Ajustes), nube fija, servidor de notificaciones (`pushNotificationServerProxy`; sin él Nextcloud usaría el suyo solo si la marca fuera «Nextcloud», que no lo es), enlaces, enlace al código fuente visible en Ajustes, grupos, sin introducción, una sola cuenta, sin informes de fallos ni perfiles de Nextcloud, color. `customer` es solo el acento (teal); se añaden `customerBackground` y `customerBackgroundText` (lienzo y tinta, claro y oscuro, de `IMAGINA_CANVAS*` e `IMAGINA_INK*`) y, al final del fichero, `NCBrandFont` (Instrument Sans por nombre; la fuente del sistema donde no está, como en las extensiones, que no la llevan). | Lo que Nextcloud deja cambiar a las versiones con otra marca, y que ninguna pantalla pinte el teal de fondo. |
| `Brand/LaunchScreen.storyboard` | Fondo con el color con nombre `ImaginaCanvas` (lienzo claro y oscuro, en `Custom.xcassets`) y el logotipo de 240 pt de ancho; antes, el acento de Imagina. | Pantalla de carga: crema con «imagina /cloud», no teal. |
| `iOSClient/NCGlobal.swift` | Esquema de la app y de las acciones de los widgets. | Que los enlaces no abran la app oficial. |
| `iOSClient/More/NCMoreModel.swift` | Tres enganches marcados «Imagina (IMAGINA.md)»: un destino `imagina` para las acciones de Imagina, su caso en `perform` y la fila «Configurar el correo» (o «Actualizar el correo») encima de «Configuración». La fila solo aparece mientras este iPhone es un dispositivo conectado; el enganche pasa una función para volver a construir el Menú cuando cambia el estado del perfil. | Que el correo del iPhone se configure desde la app. |
| `iOSClient/Login/NCLogin.swift` | Sus cinco usos de `NCBrandColor.shared.customer` (fondo de la pantalla y de la navegación, y la elección del color de los textos) pasan a `customerBackground`; y un enganche al final de `viewDidLoad`, marcado «Imagina (IMAGINA.md)»: esconde el logo de Nextcloud y pone el logotipo y «Entrar con Imagina» en lugar de la dirección del servidor. Inactivo si `IMAGINA_AUTH_HOST` está vacío. | El acceso de Nextcloud enseña sus páginas y pide autorizar dos veces. También es la pantalla a la que Nextcloud lleva cuando la contraseña de aplicación deja de valer (ver abajo). |
| `iOSClient/Account/Account Settings/NCAccountSettingsModel.swift` | Una línea tras quitar la cuenta, marcada «Imagina (IMAGINA.md)»: desconecta este iPhone en Imagina. | Que quitar la cuenta libere el dispositivo (y su plaza) en Imagina. |
| `iOSClient/AppDelegate.swift` | Tres enganches marcados «Imagina (IMAGINA.md)»: al principio de `application(_:didFinishLaunchingWithOptions:)`, `ImaginaTheme.install()` (Instrument Sans en los títulos de la barra de pestañas); al principio de `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`, `ImaginaPush.tokenArrived(deviceToken)` (el token de APNs también va a Imagina); y al principio de `userNotificationCenter(_:didReceive:withCompletionHandler:)`, `if ImaginaMailNotice.handle(response) { completionHandler(); return }` (un aviso de correo nuevo de Imagina abre el mensaje en Mail; cualquier otra respuesta sigue por el código de Nextcloud sin cambios). | Los avisos de correo nuevo (C12.6) y la tipografía de la barra de pestañas. |
| `Notification Service Extension/NotificationService.swift` | El texto de reserva de una notificación que no se puede leer dice el nombre de la app en lugar de «Nextcloud». | Marca. |
| `iOSClient/Supporting Files/*.lproj/Localizable.strings` | El texto que nombra la app en Ajustes del iPhone (`_access_photo_not_enabled_msg_`) dice `IMAGINA_APP_NAME`. | Los demás textos con «Nextcloud» hablan del servidor o usan ya el nombre de marca. |
| `iOSClient/Login/NCLoginProvider.swift`, `File Provider Extension UI/DocumentActionViewController.swift`, `iOSClient/Utility/Maintenance.swift`, `iOSClient/Utility/MigrationMultiDomains.swift` | Fondo `customerBackground` y texto `customerBackgroundText` donde pintaban `customer` y blanco (la pantalla de acceso web de reserva; el error de la app Archivos; las pantallas de mantenimiento y migración, que se ven un instante en cada versión nueva, también la primera vez); la barra de progreso va en teal. | Que ninguna pantalla pinte el teal de fondo. |
| `iOSClient/Extensions/UINavigationController+Extension.swift`, `iOSClient/More/NCMoreNavigationController.swift` | Fondo por defecto de la barra de navegación `customerBackground` (antes de iOS 26, que dibuja la suya) y Instrument Sans en el título (17 semibold) y en los botones de texto. | Barras en el lienzo y con la tipografía de la marca. |
| `iOSClient/Main/Collection Common/NCCollectionViewCommon.swift`, `iOSClient/Media/NCMedia.swift`, `iOSClient/More/NCMoreView.swift` | Fondo de la pantalla en `customerBackground` en lugar del blanco del sistema (`systemBackground`, `systemGroupedBackground`): Archivos, Favoritos, Sin conexión y demás listas que heredan de `NCCollectionViewCommon`, Media y Menú (sus tarjetas siguen blancas, como el manual: «surface» sobre «canvas»). | Pantallas principales en el lienzo. |
| `iOSClient/Settings/Settings/NCSettingsView.swift` | El pie de Ajustes (el aviso con la versión y «no es la app oficial») se dibuja con `ImaginaAboutFooter`: el logotipo encima del texto. | La pantalla «acerca de». |
| `REUSE.toml` | Una anotación al final: las fuentes de `imagina/Sources/Fonts` son OFL-1.1 (el texto está en `LICENSES/OFL-1.1.txt`). | Licencia de Instrument Sans. |
| `AppIcon.icon`, `Brand/Custom.xcassets/AppIcon.appiconset` | Icono de Imagina Cloud (ver abajo). | Marca. |
| `Brand/Custom.xcassets/logo.imageset` | El logotipo «imagina /cloud» (`logo.svg`, y `logo-dark.svg` en el tema oscuro; vectorial) en lugar del logo de Nextcloud; lo usan la pantalla de carga, el acceso, el error de la app Archivos y Ajustes. Y el color `ImaginaCanvas.colorset`, nuevo, para la pantalla de carga. | Marca. |

## Lo propio de Imagina

| Dónde | Qué |
| --- | --- |
| `imagina/apply-branding.py` | Aplica todo lo anterior desde la versión de Nextcloud de `NEXTCLOUD_IOS_TAG`. |
| `imagina/Sources/ImaginaSignIn.swift` | «Entrar con Imagina»: el logotipo y el botón (teal, texto en Instrument Sans, sobre el lienzo; a la tinta y menta en el tema oscuro) de la pantalla de acceso y OAuth con PKCE (alcance `openid cloud.devices`) contra Imagina en una `ASWebAuthenticationSession` efímera (sin el aviso «quiere usar … para iniciar sesión») que vuelve por `<id>://oauth2redirect`. Si Imagina rechaza (sin plaza, la Cloud de la persona aún no está lista…) enseña su mensaje con «Reintentar». |
| `imagina/Sources/ImaginaDevice.swift` | Este iPhone como dispositivo de Imagina: lo da de alta (`POST /devices`, plataforma `IOS`, nombre `UIDevice.current.name`) y devuelve el acceso a Nextcloud, y manda enseguida su token de APNs; al quitar la cuenta lo desconecta (`DELETE`). |
| `imagina/Sources/ImaginaApi.swift` | Las peticiones a Imagina: endpoint de tokens (con renovación; el refresh token rota) y API de dispositivos (`POST`, `GET /{id}`, `POST /{id}/mail-profile`, `PUT` y `DELETE /{id}/push`, `DELETE /{id}`). Una renovación a la vez; los rechazos de Imagina (`{"error","message"}`) llegan a la persona con su texto. |
| `imagina/Sources/ImaginaStore.swift` | El llavero propio (no el de Nextcloud): id del dispositivo, tokens, último estado del perfil de correo y el token de APNs que Imagina ya tiene para ese dispositivo, solo en este iPhone y sin copia de seguridad. Sobrevive a borrar la app. |
| `imagina/Sources/ImaginaMailSetup.swift` | «Configurar el correo»: explica los pasos que quedan en Ajustes (Permitir, Perfil descargado, Instalar), pide a la API un enlace de un solo uso (válido unos minutos) y lo abre en Safari, que es el único que puede instalar el perfil. Lo ofrece también justo después de «Entrar con Imagina». |
| `imagina/Sources/ImaginaPush.swift` | El token de APNs de este iPhone en Imagina (`PUT /devices/{id}/push`, C12.6): lo manda cuando iOS lo entrega y el dispositivo existe, y solo otra vez si cambia el token o el dispositivo; si falla, lo reintenta al volver la app a primer plano (como máximo una vez por minuto) y nunca abre «Entrar con Imagina» por esto. También pide el permiso de avisos tras entrar si sigue sin decidir. |
| `imagina/Sources/ImaginaMailNotice.swift` | El aviso de correo nuevo (`{"imagina": {"type": "new_mail", "url": "message://…"}}`): al tocarlo abre ese mensaje en Mail (solo enlaces `message://`; si no sirve, Mail a secas con `message:`). |
| `imagina/Sources/ImaginaBrand.swift` | Colores del manual de marca (lienzo, tinta, acento…, con su tema oscuro), `ImaginaTheme` (Instrument Sans en los títulos de la barra de pestañas) y textos de las pantallas de Imagina (español de España, tuteo; inglés en los demás idiomas). |
| `imagina/Sources/ImaginaAbout.swift` | `ImaginaAboutFooter`: el pie de Ajustes con el logotipo sobre el aviso de la app. |
| `imagina/Sources/Fonts/` | Instrument Sans (Regular, Medium, SemiBold y Bold), OFL-1.1: la carpeta sincronizada las copia a la raíz del paquete de la app y `UIAppFonts` las registra. Las extensiones no las llevan. |
| `imagina/Sources/ImaginaParameters.swift` | Generado por el script con los parámetros; fuera de git. |
| `imagina/brand/` | Fuentes de las imágenes de marca (el icono y los logotipos `imagina-cloud-wordmark*.svg`, tal como salen del kit de marca) y `name-fonts.py`, que escribe las fuentes de `imagina/Sources/Fonts`. |
| `imagina/GoogleService-Info.placeholder.plist` | Sustituto del fichero de Firebase que Nextcloud deja fuera de git y su proyecto copia en la app; el script lo pone en la raíz si no hay otro. Nunca se usa: la app no manda informes de fallos. |

## Cómo se conecta el iPhone

1. **Entrar**: «Entrar con Imagina» (OAuth, tokens en el llavero) → `POST /api/v1/cloud/devices` crea el dispositivo y devuelve `cloud.url`, `cloud.loginName` y `cloud.appPassword` → la app crea con eso su única cuenta de Nextcloud. Si había un dispositivo guardado de antes (se borró la app, se reinició o se perdió la cuenta), se desconecta antes de crear el nuevo: Imagina no entrega dos veces la contraseña de aplicación de un dispositivo y así no se gasta otra plaza.
2. **Tokens**: el de acceso dura 15 minutos y el de renovación 7 días (rota en cada uso). Al pedir el perfil de correo, si no se pueden renovar, se vuelve a «Entrar con Imagina» solo para conseguir un token: no se crea otro dispositivo, se sigue con el id guardado.
3. **Correo**: el Menú muestra «Configurar el correo» mientras este iPhone sea un dispositivo conectado (o «Actualizar el correo» si Imagina dice que el perfil instalado ya no coincide con los buzones: `GET /devices/{id}` → `mailProfile`). Al tocarlo se enseña el paso a paso de Ajustes y, al descargar, `POST /devices/{id}/mail-profile` da un enlace nuevo que se abre en Safari. Si Imagina contesta que el dispositivo está desconectado (410), la app lo olvida y lo dice.
4. **Imagina desconecta el dispositivo**: la contraseña de aplicación deja de valer, Nextcloud recibe un 401 (`NCMainTabBarController` lo comprueba cada 3 segundos → `NCAccount.checkRemoteUser`), quita la cuenta y presenta `NCLogin`, que aquí es el botón «Entrar con Imagina». Al volver a entrar se crea la cuenta de cero (la app es de una sola cuenta); el dispositivo guardado, si Imagina ya lo da por desconectado, se descarta y se crea otro.
5. **La persona quita la cuenta** en la app: se desconecta el dispositivo en Imagina (primero `DELETE …/push`, luego `DELETE` del dispositivo, sin esperar) y se borran del llavero el id y los tokens.

### Notificaciones (C11.5)

La app se registra, como la de Nextcloud, en el servidor de Nextcloud de la persona (`notifications`) indicando `IMAGINA_PUSH_SERVER_URL` como proxy, y en ese proxy (`POST …/devices`) con su token de APNs. Hacen falta `aps-environment` en la app (ya está) y los modos de fondo `remote-notification` (ya están). Nada apunta ya al proxy de Nextcloud (`push-notifications.nextcloud.com`) ni a Firebase: `FirebaseApp.configure()` no se llama (`disable_crash_service`) y la fase de Crashlytics está vacía. El servidor de Imagina manda con APNs de producción, así que las notificaciones solo llegan a compilaciones de TestFlight o del App Store, no a las de Xcode en un iPhone (esas usan el APNs de desarrollo).

### Avisos de correo nuevo (C12.6)

El correo del iPhone es la app Mail de Apple (configurada con el perfil de «Configurar el correo»), que no recibe push del proveedor de correo. Imagina vigila cada buzón que este iPhone lee con el perfil y, cuando llega un mensaje, manda a esta app una **alerta de APNs** (topic `build.imagina.cloud`): título «Correo nuevo», texto «En info@casapepe.com», sin `mutable-content` y con los datos `{"imagina": {"type": "new_mail", "url": "message://%3C…%3E"}}`.

- **El token llega a Imagina.** `AppDelegate` recibe el token de APNs en cada arranque (Nextcloud lo guarda y lo registra en su servidor de notificaciones, sin cambios) y el enganche se lo pasa a `ImaginaPush`, que lo manda en hexadecimal minúsculo a `PUT /api/v1/cloud/devices/{id}/push` con `{"token": "…"}` (token de acceso con alcance `cloud.devices`, renovado como siempre; 204 si va bien). Se manda cuando el token llega y el dispositivo ya existe, o justo después de que «Entrar con Imagina» cree el dispositivo si el token ya se conocía; el llavero (`ImaginaStore`) guarda qué token tiene Imagina para qué dispositivo y no se repite. Un 410 (Imagina desconectó el dispositivo) lo olvida como en el resto de la app; cualquier otro fallo, o un token de acceso que ya no se puede renovar, se reintenta cuando la app vuelve a primer plano, sin abrir «Entrar con Imagina». Al quitar la cuenta, `ImaginaDevice.disconnect` hace `DELETE …/push` y después `DELETE` del dispositivo (sin esperar).
- **Tocar el aviso abre el mensaje.** El enganche de `userNotificationCenter(_:didReceive:…)` entrega la respuesta primero a `ImaginaMailNotice`: si los datos dicen `new_mail`, abre el `url` con `UIApplication.shared.open` (esperando unos segundos a que la app esté activa si el toque la está arrancando) y, si no es un enlace `message://` o iOS no lo abre, abre `message:` (Mail). Abrir un `message://` abre exactamente ese mensaje en Mail aunque Mail aún no lo haya descargado (comprobado en un iPhone). Cualquier otra respuesta sigue por el código de Nextcloud.
- **En primer plano** el aviso se ve como banner sin cambiar nada: `willPresent` de Nextcloud ya muestra todas las notificaciones (`.list`, `.banner`, `.sound`).
- **Nextcloud no lo toca.** La extensión de notificaciones de Nextcloud solo se ejecuta con `mutable-content` (y pondría su propio texto en lugar del aviso): **el servidor de Imagina no debe ponerlo**. `didReceiveRemoteNotification` de Nextcloud solo mira `subject`, que el aviso no trae, y contesta «sin datos».
- **Permiso.** Nextcloud pide el permiso de avisos (alertas, sonido e insignia) en cada arranque, así que se decide la primera vez que se abre la app, antes de «Entrar con Imagina»; si sigue sin decidir al terminar de entrar, `ImaginaPush` lo pide entonces (iOS solo pregunta una vez).
- **Solo compilaciones de TestFlight o del App Store.** La clave de APNs de Imagina es de producción: una compilación de Xcode en un iPhone usa el APNs de desarrollo, registra un token que el servidor no puede usar, y no recibe estos avisos (ni los de Nextcloud).

## Imágenes de marca

En `imagina/brand/`: `imagina-cloud-icon-square.svg` (la loseta tinta de Imagina con la nube y el punto teal, la misma que en Android, a sangre, para el PNG del icono), `imagina-cloud-mark.svg` (la misma con esquinas redondeadas; ya no va en la app), `AppIcon-1024.png` y `AppIcon.icon` (el icono de Icon Composer: fondo tinta, la nube en marfil y el punto teal, sin brillo ni translucidez), y `imagina-cloud-wordmark.svg` y `imagina-cloud-wordmark-reverse.svg` (el logotipo «imagina /cloud», trazado, para fondos claros y oscuros). El script los copia en su sitio; a los logotipos les añade `width` y `height` (240 pt de ancho, la proporción del kit), porque los SVG del kit solo traen `viewBox`. Para regenerar el PNG tras cambiar el SVG:

```sh
qlmanage -t -s 1024 -o /tmp imagina/brand/imagina-cloud-icon-square.svg
sips -s format png -z 1024 1024 /tmp/imagina-cloud-icon-square.svg.png --out imagina/brand/AppIcon-1024.png
```

## Aspecto: el manual «Light Craft»

Reglas del sistema de diseño de Imagina («Light Craft», guía de marca) aplicadas a la app:

- **Fondo crema, teal solo para resaltar.** Las pantallas que pinta la marca y las principales van sobre el lienzo (`#F8F7F4`; `#111219` en el tema oscuro) con texto tinta (`#1A1B25`; `#F3F2EE`): pantalla de carga, acceso, error de la app Archivos, mantenimiento, Archivos, Favoritos, Media y Menú, y la barra de navegación (antes de iOS 26). El teal (`#0F766E`) es el acento: botón de «Entrar con Imagina», interruptores, selección, carpetas y la barra de pestañas, que vienen del tema del servidor (`color-element`; el fondo y el `color` del servidor no los lee la app, así que cambiar el fondo del tema del servidor a crema no cambia nada aquí). Cuando el servidor no da color, `customer` (el mismo teal) hace de reserva.
- **Logotipo donde cabe, icono donde no.** «imagina /cloud» (con su versión inversa en el tema oscuro, `logo.imageset`) en la pantalla de carga, el acceso, el error de la app Archivos y el pie de Ajustes. El icono, solo como icono de la app (y en avatares y notificaciones, que son del sistema).
- **Tipografía.** Instrument Sans (400, 500, 600 y 700) está en el paquete y registrada. Se usa en el botón y el texto del acceso, en el pie de Ajustes, en el título (17 semibold) y los botones de texto de las barras de navegación y en los títulos de la barra de pestañas. **No** en el resto: Nextcloud fija la fuente en cada etiqueta (39 xib y storyboards con fuente propia y unas 350 llamadas `.font(…)` de SwiftUI), así que cambiarla en toda la app obligaría a editar decenas de ficheros o a sustituir métodos de UIKit por otros; se queda en la fuente del sistema la lista de ficheros, Ajustes, el Menú y las hojas. Fraunces (titulares) y Geist Mono (códigos y direcciones) no se incluyen: la app no tiene titulares y los textos con direcciones son del sistema.
- **Lo que sigue con los fondos del sistema** (blanco y negro de iOS): Ajustes y sus subpantallas, la papelera, el selector de carpetas, actividad, compartir, el visor, las hojas y las ventanas de aviso, repartidos por decenas de ficheros. La introducción de Nextcloud (`Brand/Intro`) sigue pintando `customer` de fondo y con imágenes de Nextcloud, pero está desactivada (`disable_intro`): no se ve.

Las fuentes: el kit de marca trae las cuatro Instrument Sans ya cortadas, pero con el mismo nombre en las cuatro (iOS busca por nombre y se quedaría con una). `imagina/brand/name-fonts.py <carpeta de fuentes del kit>` les da su nombre (`InstrumentSans-Medium`, `-SemiBold`, `-Bold`; los glifos no se tocan) y las escribe en `imagina/Sources/Fonts`; solo hace falta volver a ejecutarlo si cambia el kit.

## Compilación automática

`.github/workflows/imagina.yml` (GitHub Actions del repositorio público `efrain-salas/imagina-cloud-ios`, en un Mac de GitHub): aplica la marca y compila la app para el simulador en cada subida a `main`, y cada lunes abre una incidencia si Nextcloud ha publicado una versión posterior a `NEXTCLOUD_IOS_TAG`. El script de marca parte de la etiqueta de Nextcloud, así que cada etiqueta nueva se sube también al fork (`git push origin <etiqueta>`). Los flujos de Nextcloud que trae el fork están desactivados en GitHub (`gh workflow disable`): usan sus propios Mac. La firma y la subida a TestFlight llegarán con la cuenta de Apple (C11.6).

## Actualizar a una nueva versión de Nextcloud

1. `git fetch upstream --tags` y `git merge <nueva>` sobre `main`. Los conflictos en ficheros que escribe el script se resuelven quedándose con cualquiera de las dos versiones: el paso 3 los reescribe.
2. Cambiar `NEXTCLOUD_IOS_TAG` en `imagina/imagina.properties` y subir la etiqueta al fork (`git push origin <nueva>`).
3. `python3 -I imagina/apply-branding.py`. Si se para, Nextcloud cambió el trozo que el script busca: revisar el cambio en Nextcloud y ajustar el script.
4. Revisar opciones de marca nuevas: `git diff <anterior> <nueva> -- Brand/NCBrand.swift`, y extensiones o grupos de app nuevos: `git diff <anterior> <nueva> -- Brand/ Nextcloud.xcodeproj/project.pbxproj | grep -i 'twsweb\|group\.'`.
5. Compilar e instalar en un iPhone y probar: «Entrar con Imagina» (la hoja se cierra sola y, al crearse la cuenta, ofrece configurar el correo), lista de ficheros, subir una foto, la app en Archivos, «Menú › Configurar el correo» hasta «Perfil instalado», desconectar el dispositivo desde Imagina y ver que la app vuelve a «Entrar con Imagina», que un correo nuevo en un buzón del perfil avisa (con la app cerrada, en segundo plano y abierta) y tocar el aviso abre el mensaje en Mail (TestFlight), y que no se vea «Nextcloud» en ninguna pantalla.

## Pendiente para la app de verdad

- Aspecto: Instrument Sans y el lienzo en las pantallas que siguen con la fuente y los fondos del sistema (ver «Aspecto»), si se quiere llegar a todas. Sin probar en un iPhone: la pestaña de Archivos, el Menú y los títulos de barras y pestañas (necesitan una cuenta); la pantalla de carga, el acceso en claro y en oscuro y su tipografía sí se han visto en el simulador.
- Probar de punta a punta con un móvil real (necesita el SMS): alta del dispositivo, cuenta, perfil de correo y reentrada tras desconectar. Está compilado y revisado, pero no ejecutado.
- Notificaciones: probar en TestFlight con la clave de APNs de Imagina. La app se registra con el agente de usuario de Nextcloud más `-Imagina` y el sufijo `(Strict VoIP)` que añade Nextcloud iOS; el servidor de Imagina tiene que tratarlo como el proxy de Nextcloud.
- Avisos de correo nuevo (C12.6): probar en TestFlight que el token llega al dispositivo en Imagina (`PUT …/push` 204), que el aviso llega con la app cerrada, en segundo plano y abierta, y que tocarlo abre el mensaje en Mail también con un arranque en frío. Sin probar en un iPhone: el toque desde un arranque en frío espera a que la app esté activa antes de abrir Mail.
- Si la persona ha denegado el permiso de avisos, la app no lo detecta ni se lo dice.
- Restablecer la app (tras fallar el código demasiadas veces) borra las cuentas sin avisar a Imagina; el siguiente «Entrar con Imagina» desconecta el dispositivo anterior y crea otro, pero hasta entonces ocupa plaza.
- El perfil de correo tiene que ir firmado (si no, iOS añade «Perfil sin firmar»): lo firma el servidor de Imagina (C7.2).
- Firma de distribución, ficha del App Store, `ITSEncryptionExportComplianceCode` propio (el de `iOSClient.plist` es de Nextcloud) y aviso de «no es la app oficial» en la ficha.
