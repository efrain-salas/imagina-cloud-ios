// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit

/// «Configurar el correo de este iPhone»: the iPhone's own Mail app gets the person's Imagina mailboxes from a
/// configuration profile, which iOS only installs from Safari. The app explains the steps that follow in Settings
/// and opens the profile's link in Safari.
///
/// Prototype (docs/PLAN_CLOUD.md, C0.12): Imagina's devices API (C7.2) will give a one-time link to a profile made
/// for this device, with every mailbox the person uses. Until then the link of a test profile comes from
/// imagina/imagina.local.properties (`IMAGINA_TEST_MAIL_PROFILE_URL`).
@MainActor
enum ImaginaMailSetup {
    struct MenuItem {
        let title: String
        let image: String
        let action: @MainActor () -> Void
    }

    /// The row of the Menu tab, or nil when there is no profile to install.
    static func menuItem(presentingFrom controller: UIViewController?) -> MenuItem? {
        guard let profileUrl = URL(string: ImaginaParameters.testMailProfileUrl), profileUrl.scheme == "https" else {
            return nil
        }
        return MenuItem(title: ImaginaText.mailSetupMenu, image: "envelope") { [weak controller] in
            explain(from: controller, profileUrl: profileUrl)
        }
    }

    private static func explain(from controller: UIViewController?, profileUrl: URL) {
        let alert = UIAlertController(title: ImaginaText.mailSetup, message: ImaginaText.mailSetupSteps, preferredStyle: .alert)
        alert.view.tintColor = ImaginaColor.accent
        alert.addAction(UIAlertAction(title: ImaginaText.cancel, style: .cancel))
        let download = UIAlertAction(title: ImaginaText.mailSetupDownload, style: .default) { _ in
            UIApplication.shared.open(profileUrl)
        }
        alert.addAction(download)
        alert.preferredAction = download
        controller?.present(alert, animated: true)
    }
}
