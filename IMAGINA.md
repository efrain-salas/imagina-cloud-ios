# Imagina Cloud para iPhone

Versión de la [app de Nextcloud para iOS](https://github.com/nextcloud/ios) con la marca de Imagina, fija a la nube de Imagina y con un único acceso: **«Entrar con Imagina»** (móvil y código SMS en una hoja del navegador que se cierra sola). Desde su «Menú», **«Configurar el correo»** pone los buzones de Imagina en la app Mail del iPhone con un perfil de configuración. Forma parte del Cloud de Imagina: `docs/PLAN_CLOUD.md` en el repositorio de Imagina (hito C11.2; prototipo en C0.12). La versión de Android es `imagina-cloud-android`, con el mismo principio.

- **Versión de Nextcloud**: `35.1.0` (`NEXTCLOUD_IOS_TAG`), el remoto `upstream`.
- **Licencia**: GPL v3 (la de la app de Nextcloud para iOS). El código de esta versión tiene que estar publicado (`IMAGINA_SOURCE_CODE_URL`, que la app enseña en Ajustes).
- **Marca**: la app no puede llevar «Nextcloud» en el nombre ni su logo, y dice en «Acerca de» y en su ficha que no es la oficial ([directrices de marca de Nextcloud](https://nextcloud.com/trademarks/)). Por eso se sustituyen el icono y el logo.

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
| `IMAGINA_CLOUD_URL` | La nube a la que la app está fija (hoy la de pruebas). |
| `IMAGINA_PUSH_SERVER_URL` | Servidor de notificaciones de Imagina (C7.10). Vacío: sin notificaciones todavía. |
| `IMAGINA_AUTH_HOST` | Servidor de identidad de Imagina. Vacío: la app usa el acceso de Nextcloud. |
| `IMAGINA_OAUTH_CLIENT_ID` | Cliente OAuth público de Imagina Cloud en Imagina (el mismo que Android). |
| `IMAGINA_PRIVACY_URL`, `IMAGINA_APP_STORE_URL`, `IMAGINA_SOURCE_CODE_URL` | Enlaces de Ajustes. |
| `IMAGINA_ACCENT` | Color del tema (el acento de Imagina); el tema del servidor puede sustituirlo. |

`imagina/imagina.local.properties` (fuera de git) sobrescribe o añade claves en cada máquina. Hoy lleva lo que la app recibirá de la API de dispositivos de Imagina (C7.1 y C7.2) cuando exista: el usuario y la contraseña de aplicación de Nextcloud de prueba (`IMAGINA_TEST_NC_USER`, `IMAGINA_TEST_NC_APP_PASSWORD`) y el enlace a un perfil de correo de prueba (`IMAGINA_TEST_MAIL_PROFILE_URL`; sin él, «Configurar el correo» no aparece).

## Cambios en ficheros de Nextcloud (los escribe el script)

| Fichero | Cambio | Motivo |
| --- | --- | --- |
| `Nextcloud.xcodeproj/project.pbxproj` | Ids de la app y de sus extensiones, equipo de firma (también a nivel de proyecto), la carpeta `imagina/Sources` sincronizada en el target `Nextcloud` y la fase «Crashlytics dSYM Upload» vacía. | Convivir con la app oficial, firmar con la cuenta de Imagina, compilar el código de Imagina sin listar ficheros a mano y no mandar nada a Firebase. |
| `Nextcloud.xcodeproj/xcshareddata/xcschemes/*.xcscheme` | Ids de las extensiones. | Que los esquemas de depuración encuentren la app. |
| `Brand/*.entitlements` | Grupos de app y grupo del llavero propios. | Los de Nextcloud son de su equipo. |
| `Brand/iOSClient.plist` | Nombre, id del esquema de URL y esquema `IMAGINA_URL_SCHEME`. | Marca y enlaces propios. |
| `Brand/File_Provider_Extension.plist`, `File_Provider_Extension_UI.plist`, `Share.plist`, `Action_Assistant.plist` | Nombre y grupo de app. | El nombre que se ve en Archivos y al compartir. |
| `Brand/NCBrand.swift` | Opciones de marca: nombre, agente de usuario, aviso de «no es la oficial», nube fija, enlaces, grupos, sin introducción, una sola cuenta, sin informes de fallos ni perfiles de Nextcloud, color. | Lo que Nextcloud deja cambiar a las versiones con otra marca. |
| `Brand/LaunchScreen.storyboard` | Fondo con el acento de Imagina. | Pantalla de carga. |
| `iOSClient/NCGlobal.swift` | Esquema de la app y de las acciones de los widgets. | Que los enlaces no abran la app oficial. |
| `iOSClient/More/NCMoreModel.swift` | Tres enganches marcados «Imagina (IMAGINA.md)»: un destino `imagina` para las acciones de Imagina, su caso en `perform` y la fila «Configurar el correo» encima de «Configuración». Sin enlace a un perfil, la fila no aparece. | Que el correo del iPhone se configure desde la app. |
| `iOSClient/Login/NCLogin.swift` | Un enganche al final de `viewDidLoad`, marcado «Imagina (IMAGINA.md)»: pone «Entrar con Imagina» en lugar de la dirección del servidor. Inactivo si `IMAGINA_AUTH_HOST` está vacío. | El acceso de Nextcloud enseña sus páginas y pide autorizar dos veces. |
| `iOSClient/Supporting Files/*.lproj/Localizable.strings` | El texto que nombra la app en Ajustes del iPhone (`_access_photo_not_enabled_msg_`) dice `IMAGINA_APP_NAME`. | Los demás textos con «Nextcloud» hablan del servidor o usan ya el nombre de marca. |
| `AppIcon.icon`, `Brand/Custom.xcassets/AppIcon.appiconset`, `Brand/Custom.xcassets/logo.imageset` | Icono y logo de Imagina Cloud (ver abajo). | Marca. |

## Lo propio de Imagina

| Dónde | Qué |
| --- | --- |
| `imagina/apply-branding.py` | Aplica todo lo anterior desde la versión de Nextcloud de `NEXTCLOUD_IOS_TAG`. |
| `imagina/Sources/ImaginaSignIn.swift` | «Entrar con Imagina»: OAuth con PKCE contra Imagina en una `ASWebAuthenticationSession` efímera (sin el aviso «quiere usar … para iniciar sesión») que vuelve por `<id>://oauth2redirect`, y las credenciales de Nextcloud del dispositivo. |
| `imagina/Sources/ImaginaMailSetup.swift` | «Configurar el correo»: explica los pasos que quedan en Ajustes (Permitir, Perfil descargado, Instalar) y abre el enlace del perfil en Safari, que es el único que puede instalarlo. |
| `imagina/Sources/ImaginaBrand.swift` | Colores del manual de marca y textos de las pantallas de Imagina (español de España, tuteo; inglés en los demás idiomas). |
| `imagina/Sources/ImaginaParameters.swift` | Generado por el script con los parámetros; fuera de git. |
| `imagina/brand/` | Fuentes de las imágenes de marca. |
| `imagina/GoogleService-Info.placeholder.plist` | Sustituto del fichero de Firebase que Nextcloud deja fuera de git y su proyecto copia en la app; el script lo pone en la raíz si no hay otro. Nunca se usa: la app no manda informes de fallos. |

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
5. Compilar e instalar en un iPhone y probar: «Entrar con Imagina» (la hoja se cierra sola), lista de ficheros, subir una foto, la app en Archivos, «Menú › Configurar el correo» hasta «Perfil instalado», y que no se vea «Nextcloud» en ninguna pantalla.

## Pendiente para la app de verdad

- Credenciales desde la API de dispositivos de Imagina (C7.1) en lugar de las de prueba; sin pantalla de autorización de Imagina (C3.1).
- Si la contraseña de aplicación deja de valer, Nextcloud vuelve a su propio acceso: llevarlo a «Entrar con Imagina».
- «Configurar el correo»: pedir a la API de dispositivos un enlace de un solo uso a un perfil firmado con todos los buzones de la persona (C7.2), en lugar del enlace de prueba; sin firma, iOS añade el aviso «Perfil sin firmar». Ofrecerlo también justo después de «Entrar con Imagina».
- Notificaciones (C11.5): servidor de notificaciones de Imagina (`IMAGINA_PUSH_SERVER_URL`) con la clave de APNs de Imagina.
- Firma de distribución, ficha del App Store, `ITSEncryptionExportComplianceCode` propio (el de `iOSClient.plist` es de Nextcloud) y aviso de «no es la app oficial» en la ficha.
