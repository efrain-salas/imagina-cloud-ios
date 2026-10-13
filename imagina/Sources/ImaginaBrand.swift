// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit

/// Colours of Imagina's brand book used by the screens Imagina adds, in the light and the dark theme. Screens are on the
/// canvas (cream) with ink text; the accent (teal) is only for the primary action and highlights, never a background.
enum ImaginaColor {
    /// canvas: the background of a screen. The brand layer paints the launch and sign-in screens with the same
    /// (`NCBrandColor.customerBackground`, from `IMAGINA_CANVAS` and `IMAGINA_CANVAS_DARK`).
    static let canvas = NCBrandColor.shared.customerBackground
    /// ink: the text on the canvas (`IMAGINA_INK`, `IMAGINA_INK_DARK`).
    static let ink = NCBrandColor.shared.customerBackgroundText
    /// ink-secondary: help text.
    static let inkSecondary = dynamic(light: 0x474B57, dark: 0xC9CBD3)
    /// accent: the primary action.
    static let accent = dynamic(light: 0x0F766E, dark: 0x2DD4BF)
    /// on-accent: the text on the accent.
    static let onAccent = dynamic(light: 0xFFFFFF, dark: 0x0B2B28)

    private static func dynamic(light: UInt32, dark: UInt32) -> UIColor {
        UIColor { traits in
            let value = traits.userInterfaceStyle == .dark ? dark : light
            return UIColor(
                red: CGFloat((value >> 16) & 0xFF) / 255.0,
                green: CGFloat((value >> 8) & 0xFF) / 255.0,
                blue: CGFloat(value & 0xFF) / 255.0,
                alpha: 1
            )
        }
    }
}

/// Instrument Sans, the brand's typeface (bundled in the app: `UIAppFonts` of iOSClient.plist), where Nextcloud's code
/// gives no hook of its own. The navigation bars take it where Nextcloud builds their appearance and the sign-in
/// screen from its own code; the font itself comes from `NCBrandFont`.
@MainActor
enum ImaginaTheme {
    /// Called when the app starts (`AppDelegate`): the titles of the tab bar.
    static func install() {
        let attributes: [NSAttributedString.Key: Any] = [.font: NCBrandFont.font(size: 10, weight: .medium)]
        for state in [UIControl.State.normal, .selected, .highlighted] {
            UITabBarItem.appearance().setTitleTextAttributes(attributes, for: state)
        }
    }
}

/// Texts of the screens Imagina adds: Spanish (Spain), tuteo, and English for any other language.
enum ImaginaText {
    private static var isSpanish: Bool {
        Locale.preferredLanguages.first?.hasPrefix("es") ?? false
    }

    static var signIn: String { isSpanish ? "Entrar con Imagina" : "Sign in with Imagina" }
    static var signInHint: String {
        isSpanish ? "Con tu móvil y un código por SMS." : "With your mobile number and a code by SMS."
    }
    static var signInFailedTitle: String { isSpanish ? "No se ha podido entrar" : "Could not sign in" }
    static var ok: String { isSpanish ? "Aceptar" : "OK" }
    static var cancel: String { isSpanish ? "Cancelar" : "Cancel" }
    static var retry: String { isSpanish ? "Reintentar" : "Try again" }
    static var notNow: String { isSpanish ? "Ahora no" : "Not now" }

    /// Imagina did not answer, or answered something the app does not understand (its refusals come with their own text).
    static var offline: String {
        isSpanish
            ? "No se ha podido conectar con Imagina. Comprueba tu conexión y vuelve a intentarlo."
            : "Could not reach Imagina. Check your connection and try again."
    }
    static var unexpected: String {
        isSpanish ? "Imagina no ha respondido como se esperaba. Vuelve a intentarlo." : "Imagina did not answer as expected. Try again."
    }
    static var needsSignIn: String {
        isSpanish ? "Tu acceso con Imagina ha caducado. Vuelve a entrar." : "Your Imagina sign-in has expired. Sign in again."
    }
    static var revoked: String {
        isSpanish
            ? "Imagina ha desconectado este iPhone. Vuelve a entrar con Imagina para seguir usando la app."
            : "Imagina has disconnected this iPhone. Sign in with Imagina again to keep using the app."
    }

    static var mailSetup: String { isSpanish ? "Configurar el correo de este iPhone" : "Set up mail on this iPhone" }
    static var mailSetupMenu: String { isSpanish ? "Configurar el correo" : "Set up mail" }
    /// The row's label when the mailboxes changed since the profile was installed.
    static var mailUpdateMenu: String { isSpanish ? "Actualizar el correo" : "Update mail" }
    static var mailSetupPreparing: String { isSpanish ? "Preparando el enlace…" : "Preparing the link…" }
    static var mailSetupFailedTitle: String { isSpanish ? "No se ha podido preparar el correo" : "Could not prepare the mail setup" }
    static var mailSetupSteps: String {
        isSpanish
            ? "Safari descargará un perfil con tu correo de Imagina. Después:\n\n1. Pulsa «Permitir».\n2. Abre Ajustes y toca «Perfil descargado».\n3. Pulsa «Instalar» y escribe el código de tu iPhone.\n\nTu correo aparecerá en la app Mail."
            : "Safari will download a profile with your Imagina mail. Then:\n\n1. Tap «Allow».\n2. Open Settings and tap «Profile Downloaded».\n3. Tap «Install» and enter your iPhone passcode.\n\nYour mail will show up in the Mail app."
    }
    static var mailSetupDownload: String { isSpanish ? "Descargar el perfil" : "Download the profile" }
}

extension ImaginaFailure {
    /// What the person reads when a request to Imagina did not work.
    var message: String {
        switch self {
        case .offline: return ImaginaText.offline
        case .needsSignIn: return ImaginaText.needsSignIn
        case .revoked: return ImaginaText.revoked
        case let .refused(message): return message
        case .unexpected: return ImaginaText.unexpected
        }
    }
}
