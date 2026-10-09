// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit
import UserNotifications

/// The notice of new mail that Imagina's server sends to this app (docs/PLAN_CLOUD.md, C12.6): an alert («Correo
/// nuevo», «En info@casapepe.com») with the data `{"imagina": {"type": "new_mail", "url": "message://%3C…%3E"}}`.
/// Tapping it opens that message in Apple's Mail app; if the link cannot be used, Mail itself.
///
/// The notice has no `mutable-content`, so Nextcloud's notification service extension never runs for it (it would
/// replace the alert with its own text); Imagina's server must keep it that way. Nextcloud's own notifications
/// carry none of this data and go on as always. While the app is in the foreground Nextcloud already shows every
/// notification as a banner, so nothing is added for that.
enum ImaginaMailNotice {
    private static let type = "new_mail"
    private static let scheme = "message"

    /// Mail itself, with no message.
    private static let mailApp = URL(string: "\(scheme):")!

    /// The link is a `message://` link of a reasonable length, and nothing else: the notice comes from outside.
    private static let longestLink = 2048

    /// A tap on a notification. Returns true when it is Imagina's notice of new mail (the caller has nothing left to
    /// do with it), false when it is anything else (Nextcloud's, whose handling goes on as always).
    nonisolated static func handle(_ response: UNNotificationResponse) -> Bool {
        guard let notice = response.notification.request.content.userInfo["imagina"] as? [AnyHashable: Any],
              notice["type"] as? String == type else {
            return false
        }
        guard response.actionIdentifier == UNNotificationDefaultActionIdentifier else {
            return true
        }

        let link = (notice["url"] as? String).flatMap(messageLink)
        Task { @MainActor in await openMail(link) }
        return true
    }

    private nonisolated static func messageLink(_ string: String) -> URL? {
        guard string.count <= longestLink,
              let url = URL(string: string),
              url.scheme?.lowercased() == scheme else {
            return nil
        }
        return url
    }

    /// Opens the message (or Mail). A tap that starts the app arrives while it is still coming up, and iOS only opens
    /// other apps from an active one: it waits a few seconds for that.
    @MainActor
    private static func openMail(_ link: URL?) async {
        var waits = 0
        while UIApplication.shared.applicationState != .active, waits < 25 {
            try? await Task.sleep(nanoseconds: 200_000_000)
            waits += 1
        }

        if let link, await UIApplication.shared.open(link) {
            return
        }
        _ = await UIApplication.shared.open(mailApp)
    }
}
