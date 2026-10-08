// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit

/// Colours of Imagina's brand book used by the screens Imagina adds.
enum ImaginaColor {
    /// brand-ink: the tile of the icon and the text on ivory.
    static let ink = UIColor(red: 0x1A / 255.0, green: 0x1B / 255.0, blue: 0x25 / 255.0, alpha: 1)
    /// ivory: the only colour on teal, as the brand book asks.
    static let ivory = UIColor(red: 0xF8 / 255.0, green: 0xF7 / 255.0, blue: 0xF4 / 255.0, alpha: 1)
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
    static var signInFailed: String {
        isSpanish ? "Imagina no ha confirmado el acceso. Vuelve a intentarlo." : "Imagina did not confirm the sign-in. Try again."
    }
    static var ok: String { isSpanish ? "Aceptar" : "OK" }
}
