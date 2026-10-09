// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import Foundation
import Security

/// Last known state of the mail profile of this device, for the label of the Menu row.
enum ImaginaMailProfileState: String, Codable {
    case notInstalled
    case installed
    /// Installed, but the person's mailboxes changed since: the profile should be installed again.
    case changed
}

/// What the app keeps about this iPhone's connection to Imagina: the device Imagina created for it (its mail profile
/// and its disconnection are asked for with that id) and the OAuth tokens that authorize those requests.
struct ImaginaSession: Codable, Equatable {
    var deviceId: String?
    var accessToken: String?
    var accessTokenExpiresAt: Date?
    var refreshToken: String?
    var mailProfile: ImaginaMailProfileState = .notInstalled

    /// An access token that is still good for at least a minute.
    var usableAccessToken: String? {
        guard let accessToken, let accessTokenExpiresAt, accessTokenExpiresAt.timeIntervalSinceNow > 60 else {
            return nil
        }
        return accessToken
    }
}

/// The session in the Keychain, in an item of its own (not Nextcloud's), readable only on this iPhone after the
/// first unlock and never copied to backups or other devices. It survives deleting the app: the next sign-in
/// disconnects whatever device it finds here before creating a new one.
enum ImaginaStore {
    private static let service = "\(ImaginaParameters.applicationId).imagina"
    private static let account = "session"
    private static let lock = NSLock()

    private static var identity: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }

    static func load() -> ImaginaSession? {
        var query = identity
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return try? JSONDecoder().decode(ImaginaSession.self, from: data)
    }

    static func save(_ session: ImaginaSession) {
        guard let data = try? JSONEncoder().encode(session) else { return }

        let status = SecItemUpdate(identity as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var attributes = identity
            attributes[kSecValueData as String] = data
            attributes[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            SecItemAdd(attributes as CFDictionary, nil)
        }
    }

    /// Changes the stored session (an empty one if there is none yet). The tokens are written from the devices API's
    /// actor and the rest from the screens, so reading, changing and writing happen under one lock.
    static func update(_ change: (inout ImaginaSession) -> Void) {
        lock.lock()
        defer { lock.unlock() }
        var session = load() ?? ImaginaSession()
        change(&session)
        save(session)
    }

    static func clear() {
        lock.lock()
        defer { lock.unlock() }
        SecItemDelete(identity as CFDictionary)
    }
}
