// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit
import UserNotifications

/// This iPhone's APNs token in Imagina (docs/PLAN_CLOUD.md, C12.6). Mail on the iPhone is Apple's Mail app, which gets
/// no push from the mail provider, so Imagina watches each mailbox this iPhone reads and sends an alert to this app
/// when mail arrives (`ImaginaMailNotice` opens the message). For that Imagina needs the token the app registers with
/// APNs: it goes to the devices API (`PUT /devices/{id}/push`) as soon as the token and the device are both known,
/// and again only when either changes. If it cannot be sent (no connection, the sign-in expired, Imagina refused),
/// the app tries again the next time it comes to the foreground; it never opens the sign-in just for this.
///
/// The token Nextcloud sends to its own push server is not touched: this is a second, independent registration.
@MainActor
enum ImaginaPush {
    /// A failed attempt is not repeated before this long.
    private static let retryDelay: TimeInterval = 60

    /// The APNs token of this app on this iPhone, as lowercase hex. Known once iOS has handed it over.
    private static var token: String?
    private static var isSending = false
    private static var lastFailure = Date.distantPast
    private static var isWatchingForeground = false

    /// iOS gave the app its APNs token (it does so every time the app starts).
    static func tokenArrived(_ deviceToken: Data) {
        token = deviceToken.isEmpty ? nil : deviceToken.map { String(format: "%02x", $0) }.joined()
        watchForeground()
        sync()
    }

    /// «Entrar con Imagina» created this iPhone's device: whatever failed before does not matter any more.
    static func deviceConnected() {
        lastFailure = .distantPast
        sync()
    }

    /// Sends the token to Imagina when Imagina does not have this one for this device yet.
    static func sync() {
        guard ImaginaSignIn.isEnabled,
              !isSending,
              let token,
              let session = ImaginaStore.load(),
              let deviceId = session.deviceId,
              session.pushRegistration != ImaginaPushRegistration(deviceId: deviceId, token: token),
              Date().timeIntervalSince(lastFailure) > retryDelay else {
            return
        }
        isSending = true

        Task {
            await send(token, to: deviceId)
            isSending = false

            // The token or the device changed while the request was on its way.
            if Self.token != token || ImaginaStore.load()?.deviceId != deviceId {
                sync()
            }
        }
    }

    private static func send(_ token: String, to deviceId: String) async {
        do {
            try await ImaginaApi.shared.registerPushToken(token, for: deviceId)
            ImaginaStore.update { session in
                if session.deviceId == deviceId {
                    session.pushRegistration = ImaginaPushRegistration(deviceId: deviceId, token: token)
                }
            }
        } catch ImaginaFailure.revoked {
            // Imagina disconnected this iPhone: the app forgets the device, as everywhere else.
            if ImaginaStore.load()?.deviceId == deviceId {
                ImaginaDevice.forgetRevoked()
            }
        } catch {
            if ImaginaStore.load()?.deviceId == deviceId {
                lastFailure = Date()
            }
        }
    }

    private static func watchForeground() {
        guard !isWatchingForeground else { return }
        isWatchingForeground = true

        NotificationCenter.default.addObserver(forName: UIApplication.didBecomeActiveNotification, object: nil, queue: .main) { _ in
            MainActor.assumeIsolated { sync() }
        }
    }

    // MARK: - Permission

    /// The alerts need the person's permission. Nextcloud asks for it when the app starts; if for any reason it is
    /// still undecided once the person has signed in with Imagina, it is asked for then (iOS asks only once).
    static func requestPermissionIfUndecided() {
        Task {
            let center = UNUserNotificationCenter.current()
            guard await center.notificationSettings().authorizationStatus == .notDetermined else { return }
            _ = try? await center.requestAuthorization(options: [.alert, .badge, .sound])
        }
    }
}
