// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit

/// This iPhone as a device of the person's Imagina Cloud (docs/PLAN_CLOUD.md, C7.1): Imagina creates it, gives it a
/// Nextcloud login that only it has, and can disconnect it, which stops that login from working.
@MainActor
enum ImaginaDevice {
    /// Creates this iPhone's device (after «Entrar con Imagina» left the tokens in the Keychain) and returns the
    /// Nextcloud login the app signs in with. The device id is kept for the mail profile and for disconnecting.
    static func connect() async throws -> ImaginaCredentials {
        // A device from before (the app was deleted or reset, or its account was lost) cannot hand its app password
        // out again: it is disconnected, which frees its seat for this one.
        if let previous = ImaginaStore.load()?.deviceId {
            ImaginaStore.update { session in
                session.deviceId = nil
                session.mailProfile = .notInstalled
                session.pushRegistration = nil
            }
            try? await ImaginaApi.shared.deleteDevice(previous)
        }

        let name = UIDevice.current.name.trimmingCharacters(in: .whitespacesAndNewlines)
        let created = try await ImaginaApi.shared.createDevice(name: name.isEmpty ? "iPhone" : String(name.prefix(80)))
        ImaginaStore.update { session in
            session.deviceId = created.deviceId
            session.mailProfile = .notInstalled
            session.pushRegistration = nil
        }
        // The notices of new mail need this iPhone's push token in Imagina (the token is already known: the app asks for
        // it every time it starts).
        ImaginaPush.deviceConnected()
        return created.credentials
    }

    /// The person removed the account from the app: this iPhone is disconnected from Imagina too (best effort, in
    /// the background) and the Keychain forgets the device and the tokens.
    static func disconnect() {
        guard let session = ImaginaStore.load() else { return }

        ImaginaStore.clear()
        Task { await ImaginaHTTP.disconnect(using: session) }
    }

    /// Imagina no longer has this device connected: the app forgets it (so the Menu stops offering the mail profile).
    /// Nextcloud's own check of the login takes the person back to «Entrar con Imagina».
    static func forgetRevoked() {
        ImaginaStore.update { session in
            session.deviceId = nil
            session.mailProfile = .notInstalled
            session.pushRegistration = nil
        }
    }
}
