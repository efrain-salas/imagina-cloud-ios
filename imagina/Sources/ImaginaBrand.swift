// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import SwiftUI
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

/// Imagina's look where Nextcloud's code gives no hook of its own. The typeface is installed when the app starts; the navigation bars take Instrument Sans where Nextcloud builds their appearance and the sign-in screen from its
/// own code (the font itself comes from `NCBrandFont`).
@MainActor
enum ImaginaTheme {
    /// Called when the app starts (`AppDelegate`): the accent as the tint of every window, the titles of the tab bar and
    /// Instrument Sans for every system font (`ImaginaFont`).
    static func install() {
        // Nextcloud tints the iPhone's bottom tab bar itself (`tabBar.tintColor`), but the iPad's floating top bar, the
        // buttons of alerts and sheets and the SwiftUI controls take the window's tint, which is the system blue. The accent
        // is adaptive (`#0F766E`; `#2DD4BF` in the dark theme). It is set on each window as it becomes visible:
        // `UIWindow.appearance().tintColor` does not reach the iPad's tab bar.
        NotificationCenter.default.addObserver(forName: UIWindow.didBecomeVisibleNotification, object: nil, queue: .main) { notification in
            (notification.object as? UIWindow)?.tintColor = ImaginaColor.accent
        }
        let attributes: [NSAttributedString.Key: Any] = [.font: NCBrandFont.font(size: 10, weight: .medium)]
        for state in [UIControl.State.normal, .selected, .highlighted] {
            UITabBarItem.appearance().setTitleTextAttributes(attributes, for: state)
        }
        ImaginaFont.install()
    }
}

/// SwiftUI's Form and List on the canvas (cream; `#111219` in the dark theme), with their rows on the system's white: the screens
/// of Settings, where Nextcloud writes `Form {` and `List {` and `apply-branding.py` writes `ImaginaForm {` and `ImaginaList {`.
/// Not by replacing `UIColor.systemGroupedBackground` at run time: a system colour replaced that way makes iOS 26 lose the
/// tint of its glass (the selected tab and the main button of an alert come out white).
struct ImaginaForm<Content: View>: View {
    private let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        Form(content: content)
            .scrollContentBackground(.hidden)
            .background(Color(ImaginaColor.canvas))
    }
}

/// `List` on the canvas, as ``ImaginaForm``.
struct ImaginaList<Content: View>: View {
    private let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        List(content: content)
            .scrollContentBackground(.hidden)
            .background(Color(ImaginaColor.canvas))
    }
}

/// Texts of the screens Imagina adds: Spanish (Spain), tuteo, and English for any other language.
enum ImaginaText {
    private static var isSpanish: Bool {
        Locale.preferredLanguages.first?.hasPrefix("es") ?? false
    }

    /// What the texts call this device: the app runs on iPhone and iPad.
    static var deviceName: String {
        UIDevice.current.userInterfaceIdiom == .pad ? "iPad" : "iPhone"
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
            ? "Imagina ha desconectado este \(deviceName). Vuelve a entrar con Imagina para seguir usando la app."
            : "Imagina has disconnected this \(deviceName). Sign in with Imagina again to keep using the app."
    }

    static var mailSetup: String { isSpanish ? "Configurar el correo de este \(deviceName)" : "Set up mail on this \(deviceName)" }
    static var mailSetupMenu: String { isSpanish ? "Configurar el correo" : "Set up mail" }
    /// The row's label when the mailboxes changed since the profile was installed.
    static var mailUpdateMenu: String { isSpanish ? "Actualizar el correo" : "Update mail" }
    static var mailSetupPreparing: String { isSpanish ? "Preparando el enlace…" : "Preparing the link…" }
    static var mailSetupFailedTitle: String { isSpanish ? "No se ha podido preparar el correo" : "Could not prepare the mail setup" }
    static var mailSetupSteps: String {
        isSpanish
            ? "Safari descargará un perfil con tu correo de Imagina. Después:\n\n1. Pulsa «Permitir».\n2. Abre Ajustes y toca «Perfil descargado».\n3. Pulsa «Instalar» y escribe el código de tu \(deviceName).\n\nTu correo aparecerá en la app Mail."
            : "Safari will download a profile with your Imagina mail. Then:\n\n1. Tap “Allow”.\n2. Open Settings and tap “Profile Downloaded”.\n3. Tap “Install” and enter your \(deviceName) passcode.\n\nYour mail will show up in the Mail app."
    }
    static var mailSetupDownload: String { isSpanish ? "Descargar el perfil" : "Download the profile" }

    /// The foot of Settings (`NCSettingsModel`): what the app is and that it is not Nextcloud's own.
    static func appNotice(version: String) -> String {
        let name = NCBrandOptions.shared.brand
        return isSpanish
            ? "\(name) para iOS \(version), una versión modificada de Nextcloud para iOS (no es la app oficial)"
            : "\(name) for iOS \(version), a modified version of Nextcloud for iOS (not the official app)"
    }

    /// The foot of Settings: the version of the server.
    static func serverNotice(version: String) -> String {
        isSpanish ? "Servidor Nextcloud \(version)" : "Nextcloud Server \(version)"
    }
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
