// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import Foundation

/// Why a request to Imagina did not give what the app needed. The texts shown to the person are in `ImaginaText`.
enum ImaginaFailure: Error {
    /// No answer from Imagina (no connection, timeout).
    case offline
    /// The tokens do not work any more (the refresh token's week is over, or Imagina revoked them): the person has to
    /// sign in again, which gives new tokens without creating anything.
    case needsSignIn
    /// Imagina no longer has this device connected (disconnected by the person or by Imagina's team).
    case revoked
    /// Imagina refused and said why in the person's language (for example, no seat left).
    case refused(message: String)
    case unexpected
}

/// The Nextcloud login of a device, as Imagina's devices API gives it.
struct ImaginaCredentials {
    let server: String
    let user: String
    let appPassword: String
}

struct ImaginaTokens {
    let accessToken: String
    let refreshToken: String?
    let expiresIn: TimeInterval
}

// MARK: - HTTP

/// The requests themselves, with no state. Everything runs on an ephemeral session: nothing is cached or kept in
/// cookies (the mail profile links are good for one use).
enum ImaginaHTTP {
    struct Response {
        let status: Int
        let data: Data
    }

    private static let session = URLSession(configuration: .ephemeral)

    private static var authBase: String { "https://\(ImaginaParameters.authHost)" }

    /// The person's languages, so Imagina answers its refusals in them.
    private static var acceptLanguage: String {
        Locale.preferredLanguages.prefix(3).enumerated()
            .map { index, language in index == 0 ? language : String(format: "%@;q=%.1f", language, max(0.5, 1 - 0.2 * Double(index))) }
            .joined(separator: ", ")
    }

    static func send(_ request: URLRequest) async throws -> Response {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw ImaginaFailure.unexpected }
            return Response(status: http.statusCode, data: data)
        } catch let failure as ImaginaFailure {
            throw failure
        } catch {
            throw ImaginaFailure.offline
        }
    }

    // MARK: OAuth

    /// Asks the token endpoint for tokens. `rejection` is what a 400 or 401 means for the caller: a refresh token
    /// that is not valid any more is `needsSignIn`; a code that did not work is `unexpected`.
    static func requestTokens(_ fields: [(String, String)], rejection: ImaginaFailure) async throws -> ImaginaTokens {
        guard let url = URL(string: "\(authBase)/oauth/token") else { throw ImaginaFailure.unexpected }

        var request = URLRequest(url: url, timeoutInterval: 20)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = formBody(fields)

        let response = try await send(request)
        switch response.status {
        case 200:
            guard let body = try? JSONSerialization.jsonObject(with: response.data) as? [String: Any],
                  let accessToken = body["access_token"] as? String, !accessToken.isEmpty else {
                throw ImaginaFailure.unexpected
            }
            let refreshToken = body["refresh_token"] as? String
            let expiresIn = (body["expires_in"] as? NSNumber)?.doubleValue ?? 900
            return ImaginaTokens(accessToken: accessToken,
                                 refreshToken: refreshToken?.isEmpty == false ? refreshToken : nil,
                                 expiresIn: expiresIn)
        case 400, 401:
            throw rejection
        default:
            throw ImaginaFailure.unexpected
        }
    }

    /// application/x-www-form-urlencoded, escaping everything but the unreserved characters.
    private static func formBody(_ fields: [(String, String)]) -> Data? {
        let unreserved = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        return fields
            .map { name, value in
                "\(name.addingPercentEncoding(withAllowedCharacters: unreserved) ?? name)=\(value.addingPercentEncoding(withAllowedCharacters: unreserved) ?? value)"
            }
            .joined(separator: "&")
            .data(using: .utf8)
    }

    // MARK: Devices API

    /// A request to `/api/v1/cloud/devices` + `path` (empty, or `/{id}`, or `/{id}/mail-profile`, or `/{id}/push`).
    static func devicesRequest(_ method: String, path: String, body: [String: Any]? = nil, token: String) throws -> URLRequest {
        guard let url = URL(string: "\(authBase)/api/v1/cloud/devices\(path)") else { throw ImaginaFailure.unexpected }

        var request = URLRequest(url: url, timeoutInterval: 20)
        request.httpMethod = method
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(acceptLanguage, forHTTPHeaderField: "Accept-Language")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        }
        return request
    }

    static func devicePath(_ deviceId: String, _ suffix: String = "") -> String {
        "/\(deviceId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? deviceId)\(suffix)"
    }

    /// Disconnects a device with the session it was stored in, once that session has been wiped from the Keychain
    /// (the person removed the account). Best effort: nothing is reported. Imagina is told to forget the push token
    /// first, so no notice of new mail is sent to an iPhone that no longer has the account.
    static func disconnect(using session: ImaginaSession) async {
        guard let deviceId = session.deviceId else { return }

        var token = session.usableAccessToken
        if token == nil, let refreshToken = session.refreshToken {
            token = try? await requestTokens(refreshFields(refreshToken), rejection: .needsSignIn).accessToken
        }
        guard let token else { return }

        if let request = try? devicesRequest("DELETE", path: devicePath(deviceId, "/push"), token: token) {
            _ = try? await send(request)
        }
        guard let request = try? devicesRequest("DELETE", path: devicePath(deviceId), token: token) else { return }
        _ = try? await send(request)
    }

    static func refreshFields(_ refreshToken: String) -> [(String, String)] {
        [
            ("grant_type", "refresh_token"),
            ("client_id", ImaginaParameters.oauthClientId),
            ("refresh_token", refreshToken)
        ]
    }
}

// MARK: - Devices API with the stored session

/// Imagina's devices API (docs/PLAN_CLOUD.md, C7.1 and C7.2) with the tokens of the stored session. An actor, so
/// two requests never refresh the (rotating) refresh token at the same time.
actor ImaginaApi {
    static let shared = ImaginaApi()

    private var refreshing: Task<String, Error>?

    // MARK: Tokens

    /// Keeps the tokens of a sign-in. The device id the app already had stays as it is.
    func store(_ tokens: ImaginaTokens) {
        ImaginaStore.update { session in
            session.accessToken = tokens.accessToken
            session.accessTokenExpiresAt = Date().addingTimeInterval(tokens.expiresIn)
            if let refreshToken = tokens.refreshToken {
                session.refreshToken = refreshToken
            }
        }
    }

    /// An access token good for a while: the stored one, or a new one from the refresh token.
    private func accessToken(renewing: Bool = false) async throws -> String {
        let session = ImaginaStore.load()
        if !renewing, let token = session?.usableAccessToken {
            return token
        }
        if let refreshing {
            return try await refreshing.value
        }
        guard let refreshToken = session?.refreshToken else { throw ImaginaFailure.needsSignIn }

        let task = Task { try await self.refresh(using: refreshToken) }
        refreshing = task
        defer { refreshing = nil }
        return try await task.value
    }

    private func refresh(using refreshToken: String) async throws -> String {
        do {
            let tokens = try await ImaginaHTTP.requestTokens(ImaginaHTTP.refreshFields(refreshToken), rejection: .needsSignIn)
            store(tokens)
            return tokens.accessToken
        } catch ImaginaFailure.needsSignIn {
            ImaginaStore.update { session in
                session.accessToken = nil
                session.accessTokenExpiresAt = nil
                session.refreshToken = nil
            }
            throw ImaginaFailure.needsSignIn
        }
    }

    /// A request to the devices API; a 401 renews the access token once.
    private func send(_ method: String, path: String = "", body: [String: Any]? = nil) async throws -> ImaginaHTTP.Response {
        let token = try await accessToken()
        let response = try await ImaginaHTTP.send(ImaginaHTTP.devicesRequest(method, path: path, body: body, token: token))
        guard response.status == 401 else { return response }

        let renewed = try await accessToken(renewing: true)
        let retried = try await ImaginaHTTP.send(ImaginaHTTP.devicesRequest(method, path: path, body: body, token: renewed))
        if retried.status == 401 { throw ImaginaFailure.needsSignIn }
        return retried
    }

    // MARK: Devices

    /// Creates this device and returns its id with its Nextcloud login (an app password only this device has).
    func createDevice(name: String) async throws -> (deviceId: String, credentials: ImaginaCredentials) {
        let response = try await send("POST", body: ["name": name, "platform": "IOS"])
        guard response.status == 201 else { throw Self.failure(response) }

        struct Created: Decodable {
            struct Device: Decodable { let id: String }
            struct Cloud: Decodable { let url: String; let loginName: String; let appPassword: String }
            let device: Device
            let cloud: Cloud
        }
        guard let created = try? JSONDecoder().decode(Created.self, from: response.data),
              !created.device.id.isEmpty,
              !created.cloud.loginName.isEmpty,
              !created.cloud.appPassword.isEmpty,
              URL(string: created.cloud.url)?.scheme == "https" else {
            throw ImaginaFailure.unexpected
        }
        return (created.device.id, ImaginaCredentials(server: created.cloud.url, user: created.cloud.loginName, appPassword: created.cloud.appPassword))
    }

    /// Whether Imagina still has the device connected and the state of its mail profile.
    func status(of deviceId: String) async throws -> (revoked: Bool, mailProfile: ImaginaMailProfileState) {
        let response = try await send("GET", path: ImaginaHTTP.devicePath(deviceId))
        guard response.status == 200 else { throw Self.failure(response, missingMeansRevoked: true) }

        struct Status: Decodable {
            struct Device: Decodable { let revoked: Bool? }
            struct MailProfile: Decodable { let installed: Bool?; let changed: Bool? }
            let device: Device?
            let revoked: Bool?
            let mailProfile: MailProfile?
        }
        guard let status = try? JSONDecoder().decode(Status.self, from: response.data) else { throw ImaginaFailure.unexpected }

        let mailProfile: ImaginaMailProfileState
        if status.mailProfile?.installed != true {
            mailProfile = .notInstalled
        } else {
            mailProfile = status.mailProfile?.changed == true ? .changed : .installed
        }
        return (status.revoked ?? status.device?.revoked ?? false, mailProfile)
    }

    /// A one-time link, good for a few minutes, to the mail profile of this device (it is opened in Safari).
    func mailProfileLink(for deviceId: String) async throws -> URL {
        let response = try await send("POST", path: ImaginaHTTP.devicePath(deviceId, "/mail-profile"))
        guard response.status == 201 else { throw Self.failure(response, missingMeansRevoked: true) }

        struct Link: Decodable { let url: String }
        guard let link = try? JSONDecoder().decode(Link.self, from: response.data),
              let url = URL(string: link.url), url.scheme == "https" else {
            throw ImaginaFailure.unexpected
        }
        return url
    }

    /// Gives Imagina this device's APNs token (hex), so it can send the notices of new mail to this iPhone. A device
    /// Imagina has disconnected answers 410 (`revoked`).
    func registerPushToken(_ token: String, for deviceId: String) async throws {
        let response = try await send("PUT", path: ImaginaHTTP.devicePath(deviceId, "/push"), body: ["token": token])
        guard response.status == 204 else { throw Self.failure(response) }
    }

    /// Disconnects a device. One that Imagina does not have any more is as good as disconnected.
    func deleteDevice(_ deviceId: String) async throws {
        let response = try await send("DELETE", path: ImaginaHTTP.devicePath(deviceId))
        guard response.status == 204 || response.status == 404 || response.status == 410 else { throw Self.failure(response) }
    }

    // MARK: Refusals

    /// `{"error": code, "message": sentence in the person's language}`.
    private static func failure(_ response: ImaginaHTTP.Response, missingMeansRevoked: Bool = false) -> ImaginaFailure {
        if response.status == 410 || (missingMeansRevoked && response.status == 404) {
            return .revoked
        }
        struct Refusal: Decodable { let message: String? }
        if let message = (try? JSONDecoder().decode(Refusal.self, from: response.data))?.message, !message.isEmpty {
            return .refused(message: message)
        }
        return .unexpected
    }
}
